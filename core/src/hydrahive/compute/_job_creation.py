"""Validated and idempotent compute-job insertion."""

from __future__ import annotations

import sqlite3
from contextlib import nullcontext

from hydrahive.compute._game_job_binding import validate_game_job_execution
from hydrahive.compute._job_codec import (
    MAX_IDEMPOTENCY_KEY,
    JobConflict,
    dump_job_json,
    row_to_job,
    validate_resource_kind,
    validate_text,
)
from hydrahive.compute._job_events import append_event
from hydrahive.compute.models import ComputeJob, JSONObject, JobResourceKind
from hydrahive.compute.providers.game_runtime_v1 import GameOperation
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

ALLOWED_OPERATIONS = frozenset(
    {
        "container.create", "container.start", "container.stop", "container.restart",
        "container.delete", "container.inspect", "vm.create_from_image", "vm.start",
        "vm.stop", "vm.restart", "vm.delete", "vm.inspect",
        *(operation.value for operation in GameOperation),
    }
)


def _request_matches(existing: ComputeJob, candidate: ComputeJob) -> bool:
    fields = (
        "node_id", "resource_kind", "resource_id", "operation", "generation", "payload",
        "created_by", "project_id", "provider", "game_resource_id", "workspace_generation",
        "source_commit_sha", "source_snapshot_digest",
    )
    return all(getattr(existing, field) == getattr(candidate, field) for field in fields)


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
    project_id: str | None = None,
    provider: str | None = None,
    game_resource_id: str | None = None,
    workspace_generation: int | None = None,
    source_commit_sha: str | None = None,
    source_snapshot_digest: str | None = None,
    connection: sqlite3.Connection | None = None,
) -> ComputeJob:
    node_id = validate_text(node_id, "node_id", maximum=128)
    resource_kind = validate_resource_kind(resource_kind)
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError("compute job operation is not allowed")
    prefix = "game" if resource_kind == "game_workspace" else resource_kind
    if not operation.startswith(f"{prefix}."):
        raise ValueError("compute job operation does not match its resource kind")
    if generation < 0:
        raise ValueError("generation must be non-negative")
    resource_id = validate_text(resource_id, "resource_id") if resource_id is not None else None
    idempotency_key = validate_text(idempotency_key, "idempotency_key", maximum=MAX_IDEMPOTENCY_KEY)
    created_by = validate_text(created_by, "created_by", maximum=128)
    payload_json = dump_job_json(payload, "payload")
    timestamp = now_iso()
    candidate = ComputeJob(
        job_id=uuid7(), node_id=node_id, resource_kind=resource_kind, resource_id=resource_id,
        operation=operation, generation=generation, payload=payload, idempotency_key=idempotency_key,
        status="queued", attempts=0, progress=0, created_by=created_by, created_at=timestamp,
        project_id=project_id, provider=provider, game_resource_id=game_resource_id,
        workspace_generation=workspace_generation, source_commit_sha=source_commit_sha,
        source_snapshot_digest=source_snapshot_digest,
    )
    if resource_kind != "game_workspace" and any(
        value is not None for value in (
            project_id, provider, game_resource_id, workspace_generation,
            source_commit_sha, source_snapshot_digest,
        )
    ):
        raise ValueError("non-game jobs cannot contain game bindings")
    with nullcontext(connection) if connection is not None else db(immediate=True) as conn:
        if resource_kind == "game_workspace":
            validate_game_job_execution(candidate, connection=conn)
        existing_row = conn.execute(
            "SELECT * FROM compute_jobs WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        if existing_row is not None:
            existing = row_to_job(existing_row)
            if not _request_matches(existing, candidate):
                raise JobConflict("idempotency key belongs to a different request")
            return existing
        node = conn.execute("SELECT kind, status FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
        accepted = node is not None and node["kind"] == "agent"
        if resource_kind != "game_workspace":
            accepted = accepted and node["status"] in {"online", "draining"}
        if not accepted:
            raise JobConflict("target compute node cannot accept jobs")
        if resource_kind != "game_workspace" and node["status"] == "draining" and operation.rsplit(".", 1)[-1] in {
            "create", "create_from_image", "start", "restart",
        }:
            raise JobConflict("draining compute node cannot accept workload activation jobs")
        conn.execute(
            """INSERT INTO compute_jobs
               (job_id, node_id, resource_kind, resource_id, operation, generation, payload_json,
                idempotency_key, status, created_by, created_at, project_id, provider,
                game_resource_id, workspace_generation, source_commit_sha, source_snapshot_digest)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate.job_id, node_id, resource_kind, resource_id, operation, generation,
                payload_json, idempotency_key, created_by, timestamp, project_id, provider,
                game_resource_id, workspace_generation, source_commit_sha, source_snapshot_digest,
            ),
        )
        append_event(
            conn, job_id=candidate.job_id, node_id=node_id, event_type="queued", data={}, actor=created_by
        )
        row = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (candidate.job_id,)).fetchone()
    return row_to_job(row)
