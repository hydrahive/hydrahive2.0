"""Butler — REST-Routen für Flow-CRUD und Registry-Meta."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import ValidationError

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._butler_route_helpers import (
    DryRunInput, FlowInput, flow_or_404, is_admin,
)
from hydrahive.butler import executor as bex
from hydrahive.butler import persistence as bp
from hydrahive.butler.models import Flow, TriggerEvent
from hydrahive.butler.registry import all_specs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/butler", tags=["butler"])


@router.get("/registry")
def get_registry(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return all_specs()


@router.get("/flows")
def list_flows(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    if is_admin(role):
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
    return flow_or_404(user, flow_id, user, role).model_dump()


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
    existing = flow_or_404(user, flow_id, user, role)
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


@router.post("/flows/{flow_id}/dry_run")
async def dry_run(
    flow_id: str,
    body: DryRunInput,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    flow = flow_or_404(user, flow_id, user, role)
    return await bex.dispatch(flow, body.event, dry_run=True)


@router.delete("/flows/{flow_id}", status_code=204)
def delete_flow(
    flow_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user, role = auth
    flow = flow_or_404(user, flow_id, user, role)
    bp.delete_flow(flow.owner, flow_id)


@router.post("/webhooks/project/{project_id}", status_code=202)
async def project_webhook(
    project_id: str,
    request_body: dict = {},
) -> dict:
    """Öffentlicher Webhook-Endpoint pro Projekt.

    Feuert alle Butler-Flows aller User die einen webhook_received-Trigger
    mit hook_id 'project:<project_id>' haben. Kein Auth — der project_id
    selbst ist das Secret (UUID7, nicht ratebar).
    """
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id)
    if not project:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")

    event = TriggerEvent(
        event_type="webhook",
        channel=f"project:{project_id}",
        payload=request_body,
    )
    fired = 0
    for flow in bp.list_flows():
        try:
            result = await bex.dispatch(flow, event)
            if result:
                fired += 1
        except Exception as e:
            logger.warning("Butler-Flow '%s' dispatch fehlgeschlagen: %s", flow.flow_id, e)
    return {"ok": True, "flows_fired": fired, "project_id": project_id}
