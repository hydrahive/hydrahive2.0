"""Durable compute-job creation, claiming, leasing, and lookup."""

from __future__ import annotations

from hydrahive.compute._job_codec import (
    MAX_IDEMPOTENCY_KEY,
    JobConflict,
    JobNotFound,
    dump_job_json,
    row_to_event,
    row_to_job,
    validate_resource_kind,
    validate_text,
)
from hydrahive.compute._job_events import append_event
from hydrahive.compute.models import JOB_STATUSES, ComputeJob, ComputeJobEvent, JSONObject, JobResourceKind
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

ALLOWED_OPERATIONS = frozenset(
    {
        "container.create",
        "container.start",
        "container.stop",
        "container.restart",
        "container.delete",
        "container.inspect",
        "vm.create_from_image",
        "vm.start",
        "vm.stop",
        "vm.restart",
        "vm.delete",
        "vm.inspect",
    }
)


def get_job(job_id: str) -> ComputeJob | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return row_to_job(row) if row else None


def list_jobs(
    *,
    node_id: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
    limit: int = 100,
) -> list[ComputeJob]:
    if status is not None and status not in JOB_STATUSES:
        raise ValueError("invalid compute job status")
    limit = max(1, min(limit, 200))
    conditions: list[str] = []
    values: list[object] = []
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


def _request_matches(existing: ComputeJob, values: tuple[object, ...]) -> bool:
    return (
        existing.node_id,
        existing.resource_kind,
        existing.resource_id,
        existing.operation,
        existing.generation,
        existing.payload,
        existing.created_by,
    ) == values


def create_job(
    *,
    node_id: str,
    resource_kind: JobResourceKind,
    resource_id: str | None,
    operation: str,
    generation: int,
    payload: JSONObject,
    idempotency_key: str,
    created_by: str,
) -> ComputeJob:
    node_id = validate_text(node_id, "node_id", maximum=128)
    resource_kind = validate_resource_kind(resource_kind)
    if operation not in ALLOWED_OPERATIONS or not operation.startswith(f"{resource_kind}."):
        raise ValueError("compute job operation is not allowed")
    if generation < 0:
        raise ValueError("generation must be non-negative")
    resource_id = validate_text(resource_id, "resource_id") if resource_id is not None else None
    idempotency_key = validate_text(idempotency_key, "idempotency_key", maximum=MAX_IDEMPOTENCY_KEY)
    created_by = validate_text(created_by, "created_by", maximum=128)
    payload_json = dump_job_json(payload, "payload")
    comparison = (node_id, resource_kind, resource_id, operation, generation, payload, created_by)
    timestamp = now_iso()
    with db(immediate=True) as conn:
        existing_row = conn.execute(
            "SELECT * FROM compute_jobs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing_row is not None:
            existing = row_to_job(existing_row)
            if not _request_matches(existing, comparison):
                raise JobConflict("idempotency key belongs to a different request")
            return existing
        node = conn.execute("SELECT kind, status FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if node is None or node["kind"] != "agent" or node["status"] not in {"online", "draining"}:
            raise JobConflict("target compute node cannot accept jobs")
        if node["status"] == "draining" and operation.endswith(".create"):
            raise JobConflict("draining compute node cannot accept create jobs")
        job_id = uuid7()
        conn.execute(
            """INSERT INTO compute_jobs
                   (job_id, node_id, resource_kind, resource_id, operation, generation,
                    payload_json, idempotency_key, status, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
            (
                job_id,
                node_id,
                resource_kind,
                resource_id,
                operation,
                generation,
                payload_json,
                idempotency_key,
                created_by,
                timestamp,
            ),
        )
        append_event(
            conn,
            job_id=job_id,
            node_id=node_id,
            event_type="queued",
            data={},
            actor=created_by,
        )
        row = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return row_to_job(row)


from hydrahive.compute._job_leases import claim_next_job, expire_leases  # noqa: E402
from hydrahive.compute._job_lifecycle import (  # noqa: E402
    cancel_job,
    fail_job,
    report_progress,
    start_job,
    succeed_job,
)

__all__ = [
    "JobConflict",
    "JobNotFound",
    "cancel_job",
    "claim_next_job",
    "create_job",
    "expire_leases",
    "fail_job",
    "get_job",
    "list_events",
    "list_jobs",
    "report_progress",
    "start_job",
    "succeed_job",
]
