"""Creation and project-scoped lookup for strict Game Studio jobs."""

from __future__ import annotations

from hydrahive.compute import game_resources
from hydrahive.compute._job_codec import row_to_job, validate_text
from hydrahive.compute.models import ComputeJob
from hydrahive.compute.providers.game_runtime_v1 import validate_game_job_request
from hydrahive.db.connection import db


def create_game_job(*, project_id: str, request: object, created_by: str) -> ComputeJob:
    from hydrahive.compute import jobs

    project_id = validate_text(project_id, "project_id", maximum=128)
    created_by = validate_text(created_by, "created_by", maximum=128)
    parsed = validate_game_job_request(request)
    workspace = game_resources.get_workspace(project_id, parsed.game_resource_id)
    if workspace is None:
        raise game_resources.ExecutionBindingError("game_resource_not_found")
    approval = game_resources.get_isolation_approval(workspace.isolation_approval_id)
    if approval is None:
        raise game_resources.ExecutionBindingError("game_isolation_approval_invalid")
    stored_payload = {
        "schema_version": 1,
        "workspace_handle": workspace.workspace_handle,
        "isolation_approval_id": workspace.isolation_approval_id,
        "isolation_profile_id": workspace.isolation_profile_id,
        "runner_version": workspace.runner_version,
        "policy_digest": workspace.policy_digest,
        "proof_digest": approval.proof_digest,
        "request": parsed.model_dump(mode="json"),
    }
    return jobs.create_job(
        node_id=workspace.node_id,
        resource_kind="game_workspace",
        resource_id=workspace.resource_id,
        operation=parsed.operation.value,
        generation=workspace.generation,
        payload=stored_payload,
        idempotency_key=parsed.idempotency_key,
        created_by=created_by,
        project_id=project_id,
        provider=workspace.provider,
        game_resource_id=workspace.resource_id,
        workspace_generation=workspace.generation,
        source_commit_sha=parsed.source_commit_sha,
        source_snapshot_digest=parsed.source_snapshot_digest,
    )


def get_project_job(project_id: str, job_id: str) -> ComputeJob | None:
    with db() as conn:
        row = conn.execute(
            """SELECT * FROM compute_jobs
               WHERE project_id = ? AND job_id = ? AND resource_kind = 'game_workspace'""",
            (project_id, job_id),
        ).fetchone()
    return row_to_job(row) if row else None


def list_project_jobs(project_id: str, *, limit: int = 100) -> list[ComputeJob]:
    limit = max(1, min(limit, 200))
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM compute_jobs
               WHERE project_id = ? AND resource_kind = 'game_workspace'
               ORDER BY created_at DESC, job_id DESC LIMIT ?""",
            (project_id, limit),
        ).fetchall()
    return [row_to_job(row) for row in rows]
