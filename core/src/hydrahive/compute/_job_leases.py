"""Atomic leasing and expiry for durable compute jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hydrahive.compute._job_codec import row_to_job
from hydrahive.compute._job_events import append_event
from hydrahive.compute.models import ComputeJob
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def claim_next_job(node_id: str, *, lease_seconds: int = 60) -> ComputeJob | None:
    if not 10 <= lease_seconds <= 300:
        raise ValueError("lease_seconds must be between 10 and 300")
    lease_until = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat().replace("+00:00", "Z")
    with db(immediate=True) as conn:
        node = conn.execute("SELECT status FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if node is None or node["status"] not in {"online", "draining"}:
            return None
        row = conn.execute(
            """SELECT * FROM compute_jobs
               WHERE node_id = ? AND status = 'queued'
                 AND (? != 'draining' OR operation NOT IN ('container.create', 'vm.create_from_image'))
               ORDER BY created_at, job_id LIMIT 1""",
            (node_id, node["status"]),
        ).fetchone()
        if row is None:
            return None
        lease_id = uuid7()
        conn.execute(
            """UPDATE compute_jobs
               SET status = 'leased', lease_id = ?, lease_until = ?, attempts = attempts + 1
               WHERE job_id = ? AND status = 'queued'""",
            (lease_id, lease_until, row["job_id"]),
        )
        append_event(
            conn,
            job_id=row["job_id"],
            node_id=node_id,
            event_type="leased",
            data={"lease_until": lease_until},
            actor=f"node:{node_id}",
        )
        claimed = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (row["job_id"],)).fetchone()
    return row_to_job(claimed)


def expire_leases() -> tuple[int, int]:
    timestamp = now_iso()
    with db(immediate=True) as conn:
        rows = conn.execute(
            """SELECT * FROM compute_jobs
               WHERE status IN ('leased', 'running') AND lease_until IS NOT NULL AND lease_until < ?""",
            (timestamp,),
        ).fetchall()
        requeued = expired = 0
        for row in rows:
            target = "queued" if row["status"] == "leased" else "expired"
            finished_at = None if target == "queued" else timestamp
            conn.execute(
                """UPDATE compute_jobs
                   SET status = ?, lease_id = NULL, lease_until = NULL, finished_at = ?
                   WHERE job_id = ?""",
                (target, finished_at, row["job_id"]),
            )
            append_event(
                conn,
                job_id=row["job_id"],
                node_id=row["node_id"],
                event_type=target,
                data={"reason": "lease_expired"},
                actor="system:compute-jobs",
            )
            requeued += target == "queued"
            expired += target == "expired"
    return requeued, expired
