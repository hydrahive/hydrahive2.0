"""``GET /api/agent-areas``: das Bereichs-Verzeichnis für den Agenten-Editor (docs/specs/agent-bereiche.md 4.1).

Angemeldet genügt. ``unassigned`` (Tools ohne Bereich) sieht nur ein Admin, alle anderen bekommen eine leere Liste.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator

from hydrahive.agents import _area_registry as registry
from hydrahive.agents import config as agent_config
from hydrahive.agents.areas import BASE_TOOLS
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded

router = APIRouter(prefix="/api/agent-areas", tags=["agent-areas"])
router_agent = APIRouter(prefix="/api/agents", tags=["agent-areas"])


@router.get("")
def get_areas(auth: Annotated[tuple[str, str], Depends(require_auth)],
              lang: Annotated[str, Query(max_length=8)] = "de") -> dict:
    _, role = auth
    return {"groups": registry.groups(lang), "areas": registry.all_areas(lang), "base": sorted(BASE_TOOLS),
            "unassigned": registry.unassigned() if role == "admin" else []}


class SuggestBody(BaseModel):
    purpose: str = Field(min_length=1, max_length=4000)
    lang: str = Field(default="de", max_length=8)

    @field_validator("purpose")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("purpose_empty")
        return v.strip()


@router_agent.post("/{agent_id}/area-suggestion")
async def suggest_areas(agent_id: str, body: SuggestBody, _: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    """Zweck-Vorschlag (Spec 4.6): nur Admin, speichert nichts. Modellfehler → 200 mit leerer Liste und ``llm_failed``."""
    from hydrahive.agents import area_suggest
    if not agent_config.get(agent_id):
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    try:
        return {"suggestions": await area_suggest.suggest(body.purpose, body.lang)}
    except area_suggest.SuggestFailed:
        return {"suggestions": [], "error": "llm_failed"}
