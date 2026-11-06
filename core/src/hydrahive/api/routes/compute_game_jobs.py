"""Project-role-scoped API for strict Game Studio compute jobs."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.compute import game_resources, jobs
from hydrahive.compute.models import ComputeJob
from hydrahive.compute.providers.game_runtime_v1 import GameJobRequest
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/api/compute/projects/{project_id}/game-jobs", tags=["compute", "game-studio"])


def _project(project_id: str, principal: AuthPrincipal, required: str) -> None:
    project = project_config.get(project_id)
    if project is None:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, principal.username, principal.role, required=required)


def _job_or_404(project_id: str, job_id: str) -> ComputeJob:
    job = jobs.get_project_job(project_id, job_id)
    if job is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_job_not_found")
    return job


def _public_job(job: ComputeJob) -> dict:
    return {
        "job_id": job.job_id,
        "project_id": job.project_id,
        "node_id": job.node_id,
        "provider": job.provider,
        "resource_kind": job.resource_kind,
        "game_resource_id": job.game_resource_id,
        "workspace_generation": job.workspace_generation,
        "operation": job.operation,
        "source_commit_sha": job.source_commit_sha,
        "source_snapshot_digest": job.source_snapshot_digest,
        "status": job.status,
        "attempts": job.attempts,
        "progress": job.progress,
        "error_code": job.error_code,
        "created_by": job.created_by,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "cancel_requested_at": job.cancel_requested_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project_game_job(
    project_id: str,
    body: GameJobRequest,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "write")
    try:
        created = jobs.create_game_job(
            project_id=project_id,
            request=body.model_dump(mode="json"),
            created_by=principal.user_id,
        )
    except game_resources.ExecutionBindingError as exc:
        code = exc.code
        http_status = status.HTTP_404_NOT_FOUND if code.endswith("_not_found") else status.HTTP_409_CONFLICT
        raise coded(http_status, code)
    except jobs.JobConflict:
        raise coded(status.HTTP_409_CONFLICT, "game_job_conflict")
    except sqlite3.IntegrityError:
        raise coded(status.HTTP_409_CONFLICT, "game_job_conflict")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "game_job_invalid", reason=str(exc))
    return _public_job(created)


@router.get("")
def list_project_game_jobs(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
    limit: int = Query(default=100, ge=1, le=200),
) -> list[dict]:
    _project(project_id, principal, "read")
    return [_public_job(job) for job in jobs.list_project_jobs(project_id, limit=limit)]


@router.get("/{job_id}")
def get_project_game_job(
    project_id: str,
    job_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "read")
    return _public_job(_job_or_404(project_id, job_id))


@router.post("/{job_id}/cancel")
def cancel_project_game_job(
    project_id: str,
    job_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _project(project_id, principal, "write")
    job = _job_or_404(project_id, job_id)
    try:
        cancelled = jobs.cancel_job(job.job_id, actor=principal.user_id)
    except jobs.JobConflict:
        raise coded(status.HTTP_409_CONFLICT, "game_job_transition_invalid")
    return _public_job(cancelled)
