"""Wissensräume E2b: Was sieht ein Agent im Datamining? (docs/specs/knowledge-spaces.md §2.4)

``GET /api/agents/{id}/knowledge`` (nur Admin) liefert die wirksame Sicht des Agenten und zählt die
Ereignisse, die er damit finden kann – Grundlage für den Bereich „Wissen“ im Agent-Editor.
Gezählt wird mit genau dem Filter, den die Datamining-Werkzeuge benutzen (``db._mirror_scope``).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.db import _mirror_groups as groups

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["knowledge"])


def _username(agent: dict) -> str:
    """Gezählt wird für den Besitzer. Im Chat gilt die Sicht des Nutzers, der mit dem Agenten spricht."""
    return str(agent.get("owner") or "")


async def _count(scope) -> int | None:
    from hydrahive.db._mirror_scope import where
    from hydrahive.db._mirror_search import _pool
    pool = _pool()
    if not pool:
        return None
    conds, params, _ = where(scope, 1)
    try:
        async with pool.acquire() as conn:
            return await conn.fetchval(f"SELECT count(*) FROM events WHERE {' AND '.join(conds)}", *params)
    except Exception as e:  # noqa: BLE001 — Zähler ist Zusatzinfo, darf die Ansicht nicht kippen
        logger.warning("knowledge count fehlgeschlagen: %s", e)
        return None


@router.get("/{agent_id}/knowledge", dependencies=[Depends(require_admin)])
async def agent_knowledge(agent_id: str) -> dict:
    from hydrahive.db._mirror_scope import scope_for
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    project_id = agent.get("project_id")
    scope = scope_for(agent, username=_username(agent), project_id=project_id)
    outward = agent.get("type") != "master" and groups.has_outward_tools(agent.get("tools"))
    return {
        "settings": agent.get("knowledge_access") or {},
        "effective": {
            "scope": scope.scope,
            "projects": list(scope.projects),
            "max_level": scope.max_level,
            "group_users": list(scope.group_users),
        },
        "limited_by_outward_tools": outward,
        "outward_tools": sorted(t for t in (agent.get("tools") or []) if t in groups.OUTWARD_TOOLS),
        "counted_for": scope.username,          # Sicht hängt im Chat vom Nutzer des Laufs ab
        "visible_events": await _count(scope),
    }
