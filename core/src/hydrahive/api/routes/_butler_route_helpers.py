from __future__ import annotations

import re

from fastapi import status
from pydantic import BaseModel, ValidationError

from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._session_access import assert_project_access
from hydrahive.butler import persistence as bp
from hydrahive.butler.models import Edge, Flow, Node, TriggerEvent

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


class FlowInput(BaseModel):
    flow_id: str
    name: str
    enabled: bool = False
    nodes: list[Node]
    edges: list[Edge]
    scope: str = "user"
    scope_id: str | None = None


class DryRunInput(BaseModel):
    event: TriggerEvent


def is_admin(role: str) -> bool:
    return role == "admin"


def build_flow(body: FlowInput, *, flow_id: str, owner: str, role: str,
               created_at: str | None = None) -> Flow:
    """Baut den Flow aus der Eingabe und prüft Graph + Registry.

    400 ``butler_flow_invalid``: Graph-Regeln verletzt (Zyklus, mehrere Trigger …).
    400 ``butler_subtype_unknown``: mindestens ein Baustein, den der Server nicht
    ausführen kann — die Subtypes stehen in ``params.subtypes``.
    """
    from hydrahive.butler.registry._validation import unknown_subtypes

    scope_id = body.scope_id
    if body.scope == "user":
        scope_id = None
    elif body.scope == "project":
        scope_id = (body.scope_id or "").strip()
        if not scope_id:
            raise coded(status.HTTP_400_BAD_REQUEST, "butler_project_scope_id_required")
        assert_project_access(scope_id, owner, role)

    try:
        flow = Flow(
            flow_id=flow_id, name=body.name, owner=owner,
            enabled=body.enabled, scope=body.scope, scope_id=scope_id,
            nodes=body.nodes, edges=body.edges, created_at=created_at,
        )
    except ValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_invalid",
                    errors=str(e))
    missing = unknown_subtypes(flow)
    if missing:
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_subtype_unknown",
                    subtypes=", ".join(missing))
    return flow


def flow_or_404(owner_query: str, flow_id: str, user: str, role: str) -> Flow:
    if not _ID_RE.match(flow_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_id_invalid")
    flow = bp.get_flow(owner_query, flow_id)
    if not flow:
        raise coded(status.HTTP_404_NOT_FOUND, "butler_flow_not_found")
    if flow.owner != user and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "butler_no_access")
    return flow
