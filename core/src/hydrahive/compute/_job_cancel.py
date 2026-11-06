"""Cancellation transitions and terminal confirmation for compute jobs."""

from __future__ import annotations

from hydrahive.compute._game_job_binding import validate_game_job_execution
from hydrahive.compute._job_codec import JobConflict, row_to_job, validate_text
from hydrahive.compute._job_events import append_event
from hydrahive.compute._job_lifecycle import TERMINAL_STATUSES, _lease, _load, _updated
from hydrahive.compute.models import ComputeJob
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db


def cancel_job(job_id: str, *, actor: str) -> ComputeJob:
    actor = validate_text(actor, "actor", maximum=128)
    with db(immediate=True) as conn:
        row = _load(conn, job_id)
        if row["status"] in TERMINAL_STATUSES:
            raise JobConflict("compute job is already terminal")
        if row["status"] == "running":
            if row["resource_kind"] != "game_workspace":
                raise JobConflict("running compute job cannot be cancelled safely")
            if row["cancel_requested_at"] is not None:
                return row_to_job(row)
            timestamp = now_iso()
            conn.execute(
                """UPDATE compute_jobs
                   SET cancel_requested_by = ?, cancel_requested_at = ?
                   WHERE job_id = ? AND status = 'running'""",
                (actor, timestamp, job_id),
            )
            append_event(
                conn, job_id=job_id, node_id=row["node_id"], event_type="cancel_requested", data={}, actor=actor
            )
            return _updated(conn, job_id)
        timestamp = now_iso()
        conn.execute(
            """UPDATE compute_jobs
               SET status = 'cancelled', lease_id = NULL, lease_until = NULL, finished_at = ?
               WHERE job_id = ?""",
            (timestamp, job_id),
        )
        append_event(
            conn, job_id=job_id, node_id=row["node_id"], event_type="cancelled", data={}, actor=actor
        )
        cancelled = _updated(conn, job_id)
        if cancelled.resource_kind == "container":
            from hydrahive.containers import remote

            remote.apply_failure(cancelled, "job_cancelled", connection=conn)
        elif cancelled.resource_kind == "vm":
            from hydrahive.vms import remote as vm_remote

            vm_remote.apply_failure(cancelled, "job_cancelled", connection=conn)
        return cancelled


def pending_game_cancel(node_id: str) -> ComputeJob | None:
    with db(immediate=True) as conn:
        rows = conn.execute(
            """SELECT * FROM compute_jobs
               WHERE node_id = ? AND resource_kind = 'game_workspace' AND status = 'running'
               ORDER BY cancel_requested_at IS NULL, cancel_requested_at, job_id""",
            (node_id,),
        ).fetchall()
        for row in rows:
            if row["cancel_requested_at"] is None:
                try:
                    validate_game_job_execution(row_to_job(row), connection=conn)
                except ValueError as exc:
                    timestamp = now_iso()
                    reason = getattr(exc, "code", "game_execution_binding_invalid")
                    conn.execute(
                        """UPDATE compute_jobs
                           SET cancel_requested_by = 'system:binding-invalidated', cancel_requested_at = ?
                           WHERE job_id = ? AND status = 'running' AND cancel_requested_at IS NULL""",
                        (timestamp, row["job_id"]),
                    )
                    append_event(
                        conn,
                        job_id=row["job_id"],
                        node_id=node_id,
                        event_type="cancel_requested",
                        data={"reason": reason},
                        actor="system:binding-invalidated",
                    )
                    row = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (row["job_id"],)).fetchone()
                else:
                    continue
            return row_to_job(row)
    return None


def confirm_game_job_cancelled(job_id: str, lease_id: str, *, node_id: str) -> ComputeJob:
    with db(immediate=True) as conn:
        row = _load(conn, job_id)
        if row["node_id"] != node_id or row["resource_kind"] != "game_workspace":
            raise JobConflict("game job does not belong to authenticated node")
        if row["status"] == "cancelled":
            return row_to_job(row)
        if row["status"] != "running" or row["cancel_requested_at"] is None:
            raise JobConflict("game job cancellation was not requested")
        _lease(row, lease_id)
        timestamp = now_iso()
        conn.execute(
            """UPDATE compute_jobs
               SET status = 'cancelled', lease_id = NULL, lease_until = NULL, finished_at = ?
               WHERE job_id = ?""",
            (timestamp, job_id),
        )
        append_event(
            conn,
            job_id=job_id,
            node_id=node_id,
            event_type="cancelled",
            data={"confirmed_by_node": True},
            actor=f"node:{node_id}",
        )
        return _updated(conn, job_id)
