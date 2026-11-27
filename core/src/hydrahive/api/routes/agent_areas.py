"""``GET /api/agent-areas``: das Bereichs-Verzeichnis für den Agenten-Editor (docs/specs/agent-bereiche.md 4.1).

Angemeldet genügt. ``unassigned`` (Tools ohne Bereich) sieht nur ein Admin, alle anderen bekommen eine leere Liste.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.agents import _area_registry as registry
from hydrahive.agents.areas import BASE_TOOLS
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

router = APIRouter(prefix="/api/agent-areas", tags=["agent-areas"])
agent_router = APIRouter(prefix="/api/agents", tags=["agent-areas"])


@router.get("")
def get_areas(auth: Annotated[tuple[str, str], Depends(require_auth)],
              lang: Annotated[str, Query(max_length=8)] = "de") -> dict:
    _, role = auth
    return {"groups": registry.groups(lang), "areas": registry.all_areas(lang), "base": sorted(BASE_TOOLS),
            "unassigned": registry.unassigned() if role == "admin" else []}


@agent_router.get("/{agent_id}/areas")
def get_agent_areas(agent_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Bereichs-Status eines Agenten (Besitzer oder Admin, fremd → 404 wie ``/tool-pool``). Nur lesend: gespeichert wird
    über das bestehende ``PATCH /api/agents/{id}`` (Admin, Spec 4.8); ``editable`` sagt der Oberfläche, ob das geht."""
    from hydrahive.agents import config as agent_config
    from hydrahive.agents.area_state import area_states
    from hydrahive.api.routes._agent_schemas import check_agent_access
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    check_agent_access(agent, *auth)
    return {"areas": area_states(agent), "editable": auth[1] == "admin"}
