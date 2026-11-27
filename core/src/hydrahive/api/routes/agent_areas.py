"""``GET /api/agent-areas``: das Bereichs-Verzeichnis für den Agenten-Editor (docs/specs/agent-bereiche.md 4.1).

Angemeldet genügt. ``unassigned`` (Tools ohne Bereich) sieht nur ein Admin, alle anderen bekommen eine leere Liste.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from hydrahive.agents import _area_registry as registry
from hydrahive.agents.areas import BASE_TOOLS
from hydrahive.api.middleware.auth import require_auth

router = APIRouter(prefix="/api/agent-areas", tags=["agent-areas"])


@router.get("")
def get_areas(auth: Annotated[tuple[str, str], Depends(require_auth)],
              lang: Annotated[str, Query(max_length=8)] = "de") -> dict:
    _, role = auth
    return {"groups": registry.groups(lang), "areas": registry.all_areas(lang), "base": sorted(BASE_TOOLS),
            "unassigned": registry.unassigned() if role == "admin" else []}
