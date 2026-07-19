"""Cancellation transition for queued or leased compute jobs."""

from __future__ import annotations

from hydrahive.compute._job_codec import JobConflict, validate_text
from hydrahive.compute._job_events import append_event
from hydrahive.compute._job_lifecycle import TERMINAL_STATUSES, _load, _updated
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
            raise JobConflict("running compute job cannot be cancelled safely")
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
            node_id=row["node_id"],
            event_type="cancelled",
            data={},
            actor=actor,
        )
        cancelled = _updated(conn, job_id)
        if cancelled.resource_kind == "container":
            from hydrahive.containers import remote

            remote.apply_failure(cancelled, "job_cancelled", connection=conn)
        return cancelled
