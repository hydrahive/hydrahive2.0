"""Authenticated, ownership-scoped compute-job status API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.compute import jobs
from hydrahive.compute.models import ComputeJob, ComputeJobEvent

router = APIRouter(prefix="/api/compute/jobs", tags=["compute"])


def _visible(job: ComputeJob, principal: AuthPrincipal) -> bool:
    return principal.role == "admin" or job.created_by == principal.user_id


def _job_or_404(job_id: str, principal: AuthPrincipal) -> ComputeJob:
    job = jobs.get_job(job_id)
    if job is None or not _visible(job, principal):
        raise coded(status.HTTP_404_NOT_FOUND, "compute_job_not_found")
    return job


def _public_job(job: ComputeJob) -> dict:
    return {
        "job_id": job.job_id,
        "node_id": job.node_id,
        "resource_kind": job.resource_kind,
        "resource_id": job.resource_id,
        "operation": job.operation,
        "generation": job.generation,
        "status": job.status,
        "attempts": job.attempts,
        "progress": job.progress,
        "error_code": job.error_code,
        "created_by": job.created_by,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "lease_until": job.lease_until,
    }


def _public_event(event: ComputeJobEvent) -> dict:
    data: dict = {}
    if event.event_type == "progress":
        data = {"progress": event.data.get("progress")}
    elif event.event_type == "failed":
        data = {"error_code": event.data.get("error_code")}
    elif event.event_type in {"requeued", "expired"}:
        data = {"reason": event.data.get("reason")}
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "data": data,
        "created_at": event.created_at,
    }


@router.get("")
def list_compute_jobs(
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
    node_id: str | None = Query(default=None, max_length=128),
    job_status: str | None = Query(default=None, alias="status", max_length=32),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[dict]:
    try:
        found = jobs.list_jobs(
            node_id=node_id,
            status=job_status,
            created_by=None if principal.role == "admin" else principal.user_id,
            limit=limit,
        )
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "compute_job_filter_invalid")
    return [_public_job(job) for job in found]


@router.get("/{job_id}")
def get_compute_job(
    job_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    return _public_job(_job_or_404(job_id, principal))


@router.get("/{job_id}/events")
def list_compute_job_events(
    job_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> list[dict]:
    _job_or_404(job_id, principal)
    return [_public_event(event) for event in jobs.list_events(job_id)]


@router.post("/{job_id}/cancel")
def cancel_compute_job(
    job_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    _job_or_404(job_id, principal)
    try:
        cancelled = jobs.cancel_job(job_id, actor=principal.user_id)
    except jobs.JobConflict:
        raise coded(status.HTTP_409_CONFLICT, "compute_job_transition_invalid")
    return _public_job(cancelled)
