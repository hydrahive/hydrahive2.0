"""Validation and SQLite codecs for durable compute jobs."""

from __future__ import annotations

import json
import sqlite3

from hydrahive.compute._node_codec import dump_json, load_json
from hydrahive.compute.models import (
    JOB_RESOURCE_KINDS,
    JOB_STATUSES,
    ComputeJob,
    ComputeJobEvent,
    JSONObject,
    JobResourceKind,
)

MAX_JOB_TEXT = 255
MAX_IDEMPOTENCY_KEY = 255


class JobConflict(ValueError):
    pass


class JobNotFound(ValueError):
    pass


def validate_text(value: str, field: str, *, maximum: int = MAX_JOB_TEXT) -> str:
    value = value.strip()
    if not value or len(value) > maximum:
        raise ValueError(f"{field} must contain 1-{maximum} characters")
    return value


def validate_resource_kind(value: str) -> JobResourceKind:
    if value not in JOB_RESOURCE_KINDS:
        raise ValueError("invalid compute job resource kind")
    return value  # type: ignore[return-value]


def dump_job_json(value: JSONObject, field: str) -> str:
    return dump_json(value, field)


def row_to_job(row: sqlite3.Row) -> ComputeJob:
    return ComputeJob(
        job_id=row["job_id"],
        node_id=row["node_id"],
        resource_kind=row["resource_kind"],
        resource_id=row["resource_id"],
        operation=row["operation"],
        generation=row["generation"],
        payload=load_json(row["payload_json"], "payload"),
        idempotency_key=row["idempotency_key"],
        status=row["status"],
        lease_id=row["lease_id"],
        lease_until=row["lease_until"],
        attempts=row["attempts"],
        progress=row["progress"],
        error_code=row["error_code"],
        error_params=(load_json(row["error_params_json"], "error_params") if row["error_params_json"] else None),
        created_by=row["created_by"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def row_to_event(row: sqlite3.Row) -> ComputeJobEvent:
    data = json.loads(row["data_json"])
    if not isinstance(data, dict):
        raise ValueError("stored job event data must be an object")
    return ComputeJobEvent(
        event_id=row["event_id"],
        job_id=row["job_id"],
        sequence=row["sequence"],
        event_type=row["event_type"],
        data=data,
        created_at=row["created_at"],
    )


def validate_job_status(value: str) -> None:
    if value not in JOB_STATUSES:
        raise ValueError("invalid stored compute job status")
