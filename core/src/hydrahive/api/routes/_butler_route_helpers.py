from __future__ import annotations

import re

from fastapi import status
from pydantic import BaseModel

from hydrahive.api.middleware.errors import coded
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


def flow_or_404(owner_query: str, flow_id: str, user: str, role: str) -> Flow:
    if not _ID_RE.match(flow_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "butler_flow_id_invalid")
    flow = bp.get_flow(owner_query, flow_id)
    if not flow:
        raise coded(status.HTTP_404_NOT_FOUND, "butler_flow_not_found")
    if flow.owner != user and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "butler_no_access")
    return flow
