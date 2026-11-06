"""Durable compute-job creation, claiming, leasing, and lookup."""

from __future__ import annotations

from hydrahive.compute._job_codec import JobConflict, JobNotFound, row_to_event, row_to_job
from hydrahive.compute.models import JOB_STATUSES, ComputeJob, ComputeJobEvent
from hydrahive.db.connection import db


def get_job(job_id: str) -> ComputeJob | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return row_to_job(row) if row else None


def list_jobs(
    *,
    node_id: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
    include_game: bool = True,
    limit: int = 100,
) -> list[ComputeJob]:
    if status is not None and status not in JOB_STATUSES:
        raise ValueError("invalid compute job status")
    limit = max(1, min(limit, 200))
    conditions: list[str] = []
    values: list[object] = []
    if not include_game:
        conditions.append("resource_kind != 'game_workspace'")
    for column, value in (("node_id", node_id), ("status", status), ("created_by", created_by)):
        if value is not None:
            conditions.append(f"{column} = ?")
            values.append(value)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    values.append(limit)
    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM compute_jobs {where} ORDER BY created_at DESC, job_id DESC LIMIT ?",
            values,
        ).fetchall()
    return [row_to_job(row) for row in rows]


def list_events(job_id: str) -> list[ComputeJobEvent]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM compute_job_events WHERE job_id = ? ORDER BY sequence",
            (job_id,),
        ).fetchall()
    return [row_to_event(row) for row in rows]


from hydrahive.compute._game_jobs import create_game_job, get_project_job, list_project_jobs  # noqa: E402
from hydrahive.compute._job_cancel import cancel_job, confirm_game_job_cancelled  # noqa: E402
from hydrahive.compute._job_creation import create_job  # noqa: E402
from hydrahive.compute._job_leases import claim_next_job, expire_leases  # noqa: E402
from hydrahive.compute._job_lifecycle import (  # noqa: E402
    fail_job,
    renew_job_lease,
    report_progress,
    start_job,
    succeed_job,
)

__all__ = [
    "JobConflict",
    "JobNotFound",
    "cancel_job",
    "claim_next_job",
    "confirm_game_job_cancelled",
    "create_game_job",
    "create_job",
    "expire_leases",
    "fail_job",
    "get_job",
    "get_project_job",
    "list_events",
    "list_jobs",
    "list_project_jobs",
    "renew_job_lease",
    "report_progress",
    "start_job",
    "succeed_job",
]
