"""Butler — REST-Routen für Flow-CRUD und Registry-Meta.

Phase 1: nur CRUD + Registry-Listing. Dry-Run und Trigger-Hooks
kommen in Phase 2/4.
"""
from __future__ import annotations

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ValidationError

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.butler import executor as bex
from hydrahive.butler import persistence as bp
from hydrahive.butler.models import Edge, Flow, Node, TriggerEvent
from hydrahive.butler.registry import all_specs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/butler", tags=["butler"])

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _is_admin(role: str) -> bool:
    return role == "admin"


def _flow_or_404(owner_query: str, flow_id: str, user: str, role: str) -> Flow:
    if not _ID_RE.match(flow_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_id_invalid")
    flow = bp.get_flow(owner_query, flow_id)
    if not flow:
        raise coded(status.HTTP_404_NOT_FOUND, "butler_flow_not_found")
    if flow.owner != user and not _is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "butler_no_access")
    return flow


class FlowInput(BaseModel):
    flow_id: str
    name: str
    enabled: bool = False
    nodes: list[Node]
    edges: list[Edge]
    scope: str = "user"
    scope_id: str | None = None


@router.get("/registry")
def get_registry(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return all_specs()


@router.get("/flows")
def list_flows(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    if _is_admin(role):
        flows = bp.list_flows(owner=None)
    else:
        flows = bp.list_flows(owner=user)
    return [f.model_dump() for f in flows]


@router.get("/flows/{flow_id}")
def get_flow(
    flow_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    return _flow_or_404(user, flow_id, user, role).model_dump()


@router.post("/flows", status_code=201)
def create_flow(
    body: FlowInput,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, _ = auth
    if not _ID_RE.match(body.flow_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_id_invalid")
    if bp.get_flow(user, body.flow_id):
        raise coded(status.HTTP_409_CONFLICT, "butler_flow_id_taken")
    try:
        flow = Flow(
            flow_id=body.flow_id, name=body.name, owner=user,
            enabled=body.enabled, scope=body.scope, scope_id=body.scope_id,
            nodes=body.nodes, edges=body.edges,
        )
    except ValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_invalid",
                    errors=str(e))
    bp.save_flow(flow, modified_by=user)
    return flow.model_dump()


@router.put("/flows/{flow_id}")
def update_flow(
    flow_id: str,
    body: FlowInput,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    existing = _flow_or_404(user, flow_id, user, role)
    if body.flow_id != flow_id:
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_id_mismatch")
    try:
        flow = Flow(
            flow_id=flow_id, name=body.name, owner=existing.owner,
            enabled=body.enabled, scope=body.scope, scope_id=body.scope_id,
            nodes=body.nodes, edges=body.edges,
            created_at=existing.created_at,
        )
    except ValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_invalid",
                    errors=str(e))
    bp.save_flow(flow, modified_by=user)
    return flow.model_dump()


class DryRunInput(BaseModel):
    event: TriggerEvent


@router.post("/flows/{flow_id}/dry_run")
async def dry_run(
    flow_id: str,
    body: DryRunInput,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    flow = _flow_or_404(user, flow_id, user, role)
    return await bex.dispatch(flow, body.event, dry_run=True)


@router.delete("/flows/{flow_id}", status_code=204)
def delete_flow(
    flow_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user, role = auth
    flow = _flow_or_404(user, flow_id, user, role)
    bp.delete_flow(flow.owner, flow_id)
