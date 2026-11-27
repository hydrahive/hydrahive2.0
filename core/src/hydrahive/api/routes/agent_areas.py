"""Bereichs-Routen (docs/specs/agent-bereiche.md 4.1, 4.3, 4.6, 4.8).

- ``GET /api/agent-areas``: Bereichs-Verzeichnis. Angemeldet genügt; ``unassigned`` (Tools ohne Bereich) nur für Admins.
- ``GET /api/agents/{id}/areas``: Bereichs-Status eines Agenten (Besitzer oder Admin), nur lesend.
- ``POST /api/agents/{id}/area-suggestion``: Zweck-Vorschlag (nur Admin), speichert nichts.
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
agent_router = APIRouter(prefix="/api/agents", tags=["agent-areas"])


@router.get("")
def get_areas(auth: Annotated[tuple[str, str], Depends(require_auth)],
              lang: Annotated[str, Query(max_length=8)] = "de") -> dict:
    _, role = auth
    return {"groups": registry.groups(lang), "areas": registry.all_areas(lang), "base": sorted(BASE_TOOLS),
            "unassigned": registry.unassigned() if role == "admin" else []}


@agent_router.get("/{agent_id}/areas")
def get_agent_areas(agent_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Bereichs-Status eines Agenten (Besitzer oder Admin, fremd → 403 ``agent_no_access`` wie ``/tool-pool``). Nur lesend: gespeichert wird
    über das bestehende ``PATCH /api/agents/{id}`` (Admin, Spec 4.8); ``editable`` sagt der Oberfläche, ob das geht."""
    from hydrahive.agents.area_state import area_states
    from hydrahive.api.routes._agent_schemas import check_agent_access
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    check_agent_access(agent, *auth)
    return {"areas": area_states(agent), "editable": auth[1] == "admin"}


class SuggestBody(BaseModel):
    purpose: str = Field(min_length=1, max_length=4000)
    lang: str = Field(default="de", max_length=8)

    @field_validator("purpose")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("purpose_empty")
        return v.strip()


@agent_router.post("/{agent_id}/area-suggestion")
async def suggest_areas(agent_id: str, body: SuggestBody, _: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    """Zweck-Vorschlag (Spec 4.6): nur Admin, speichert nichts. Modellfehler → 200 mit leerer Liste und ``llm_failed``."""
    from hydrahive.agents import area_suggest
    if not agent_config.get(agent_id):
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    try:
        return {"suggestions": await area_suggest.suggest(body.purpose, body.lang)}
    except area_suggest.SuggestFailed:
        return {"suggestions": [], "error": "llm_failed"}


audit_router = APIRouter(prefix="/api/admin", tags=["agent-areas"])


@audit_router.get("/area-audit")
def get_area_audit(_: Annotated[tuple[str, str], Depends(require_admin)], lang: Annotated[str, Query(max_length=8)] = "de",
                   limit: Annotated[int, Query(ge=1, le=500)] = 100) -> dict:
    """Protokoll in Bereichssprache (Spec 4.7), nur Admin, nur lesend: wer wann welchen Bereich für wen freigegeben oder
    entzogen hat. Gefiltert nach Aktion (nicht nach Ziel), Tool-Namen auf Bereichsnamen abgebildet."""
    from hydrahive.agents import area_audit
    return {"entries": area_audit.entries(lang if lang in ("de", "en") else "de", limit)}


@audit_router.get("/area-never")
def get_area_never(_: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    """Bereiche, deren Tools ``tool_pools.check_item`` ALLE ablehnt (nie per Auftrag vergebbar). Die Oberfläche graut sie aus;
    entschieden wird hier, mit demselben Maßstab wie beim Speichern, nicht mit einer zweiten Liste im Frontend."""
    from hydrahive.agents import tool_pools

    def never(tool: str) -> bool:
        try:
            tool_pools.check_item(tool)
            return False
        except ValueError:
            return True
    return {"areas": sorted(a["id"] for a in registry.all_areas("de") if a["tools"] and all(never(t) for t in a["tools"]))}
