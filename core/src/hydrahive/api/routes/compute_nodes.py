"""Authenticated administration API for compute nodes and enrollments."""

from __future__ import annotations

import hmac
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.compute import enrollment
from hydrahive.compute import db as node_db
from hydrahive.compute._node_codec import normalize_certificate_fingerprint

router = APIRouter(prefix="/api/compute", tags=["compute"])


class EnrollmentCreate(BaseModel):
    requested_name: str = Field(min_length=1, max_length=128)
    ttl_seconds: int = Field(default=900, ge=30, le=3600)


class ApprovalRequest(BaseModel):
    certificate_fingerprint: str = Field(min_length=64, max_length=95)


def _node_or_404(node_id: str):
    node = node_db.get_node(node_id)
    if node is None:
        raise coded(status.HTTP_404_NOT_FOUND, "compute_node_not_found")
    return node


def _transition(node_id: str, target: str, actor: str):
    current = _node_or_404(node_id)
    if current.status == "pending" and target == "disabled":
        raise coded(status.HTTP_409_CONFLICT, "compute_pending_node_must_be_approved_or_revoked")
    try:
        node = node_db.transition_node_status(
            node_id,
            target,  # type: ignore[arg-type]
            actor=actor,
        )
    except ValueError as exc:
        raise coded(status.HTTP_409_CONFLICT, "compute_node_transition_invalid", reason=str(exc))
    return asdict(node)


@router.get("/nodes")
def list_compute_nodes(
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> list[dict]:
    return [asdict(node) for node in node_db.list_nodes()]


@router.get("/nodes/{node_id}")
def get_compute_node(
    node_id: str,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    return asdict(_node_or_404(node_id))


@router.post("/enrollments", status_code=status.HTTP_201_CREATED)
def create_enrollment(
    body: EnrollmentCreate,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    actor = auth.user_id
    requested_name = body.requested_name.strip()
    if any(node.name == requested_name for node in node_db.list_nodes()):
        raise coded(status.HTTP_409_CONFLICT, "compute_node_name_exists")
    try:
        created = enrollment.create_token(
            requested_name=requested_name,
            created_by=actor,
            ttl_seconds=body.ttl_seconds,
        )
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "compute_enrollment_invalid", reason=str(exc))
    return asdict(created)


@router.post("/nodes/{node_id}/approve")
def approve_compute_node(
    node_id: str,
    body: ApprovalRequest,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    actor = auth.user_id
    node = _node_or_404(node_id)
    try:
        supplied = normalize_certificate_fingerprint(body.certificate_fingerprint)
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "compute_fingerprint_invalid")
    if (
        node.certificate_fingerprint is None
        or supplied is None
        or not hmac.compare_digest(
            node.certificate_fingerprint,
            supplied,
        )
    ):
        raise coded(status.HTTP_409_CONFLICT, "compute_fingerprint_mismatch")
    try:
        approved = node_db.approve_node(node_id, actor)
    except ValueError as exc:
        raise coded(status.HTTP_409_CONFLICT, "compute_node_approval_invalid", reason=str(exc))
    return asdict(approved)


@router.post("/nodes/{node_id}/drain")
def drain_compute_node(
    node_id: str,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    return _transition(node_id, "draining", auth.user_id)


@router.post("/nodes/{node_id}/disable")
def disable_compute_node(
    node_id: str,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    return _transition(node_id, "disabled", auth.user_id)


@router.post("/nodes/{node_id}/enable")
def enable_compute_node(
    node_id: str,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    return _transition(node_id, "online", auth.user_id)


@router.delete("/nodes/{node_id}")
def revoke_compute_node(
    node_id: str,
    auth: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    actor = auth.user_id
    _node_or_404(node_id)
    try:
        node = node_db.revoke_node(node_id, actor=actor)
    except ValueError as exc:
        raise coded(status.HTTP_409_CONFLICT, "compute_node_revoke_invalid", reason=str(exc))
    return asdict(node)
