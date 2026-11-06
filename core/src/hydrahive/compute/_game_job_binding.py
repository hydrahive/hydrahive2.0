"""Exact execution-binding checks shared by Game-job queue, lease, and start gates."""

from __future__ import annotations

import sqlite3

from hydrahive.compute import game_resources
from hydrahive.compute._job_codec import dump_job_json, row_to_job
from hydrahive.compute._job_events import append_event
from hydrahive.compute.models import ComputeJob, ExecutionBinding
from hydrahive.compute.providers.game_runtime_v1 import GameRuntimeStoredPayload, validate_stored_payload
from hydrahive.db._utils import now_iso


def validate_game_job_execution(
    job: ComputeJob,
    *,
    connection: sqlite3.Connection | None = None,
) -> GameRuntimeStoredPayload:
    if job.resource_kind != "game_workspace":
        raise ValueError("compute job is not a game job")
    if not all((job.project_id, job.game_resource_id, job.provider, job.workspace_generation)):
        raise game_resources.ExecutionBindingError("game_execution_binding_mismatch")
    payload = validate_stored_payload(job.payload)
    request = payload.request
    if (
        job.provider != "game-runtime/v1"
        or job.resource_id != job.game_resource_id
        or job.generation != job.workspace_generation
        or request.game_resource_id != job.game_resource_id
        or request.operation != job.operation
        or request.source_commit_sha != job.source_commit_sha
        or request.source_snapshot_digest != job.source_snapshot_digest
    ):
        raise game_resources.ExecutionBindingError("game_execution_binding_mismatch")
    binding = ExecutionBinding(
        project_id=job.project_id,
        resource_id=job.game_resource_id,
        node_id=job.node_id,
        workspace_handle=payload.workspace_handle,
        workspace_generation=job.workspace_generation,
        isolation_approval_id=payload.isolation_approval_id,
        isolation_profile_id=payload.isolation_profile_id,
        runner_version=payload.runner_version,
        policy_digest=payload.policy_digest,
        proof_digest=payload.proof_digest,
    )
    game_resources.validate_execution_binding(binding, connection=connection)
    return payload


def reject_game_job_in_connection(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    reason: str,
) -> ComputeJob:
    timestamp = now_iso()
    params = {"reason": reason}
    conn.execute(
        """UPDATE compute_jobs
           SET status = 'failed', error_code = 'job_rejected', error_params_json = ?,
               lease_id = NULL, lease_until = NULL, finished_at = ?
           WHERE job_id = ?""",
        (dump_job_json(params, "error_params"), timestamp, row["job_id"]),
    )
    append_event(
        conn,
        job_id=row["job_id"],
        node_id=row["node_id"],
        event_type="failed",
        data={"error_code": "job_rejected", "error_params": params},
        actor="system:compute-jobs",
    )
    updated = conn.execute("SELECT * FROM compute_jobs WHERE job_id = ?", (row["job_id"],)).fetchone()
    return row_to_job(updated)
