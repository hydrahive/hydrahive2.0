"""find_tools – passende Werkzeuge im Katalog finden (Katalog, Spec S7/K3).

Sucht NUR innerhalb der Freigabe des Laufs (``effective_tool_names``, Spec S6): Der Katalog erweitert nie ein Recht, und ein
gesperrtes Tool taucht weder mit Namen noch mit Beschreibung oder Schema auf. Aufgerufen wird das Gefundene mit
``run_tool(name, args)``. Das Tool steht in der Registry, ist aber in keiner Agenten-Config und keiner Standard-Liste.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_MAX_LIMIT = 10
_DEFAULT_LIMIT = 5
_HINT = "Aufruf mit run_tool(name, args); args genau nach input_schema."

_DESCRIPTION = (
    "Sucht passende Werkzeuge im Katalog (nur solche, die du nutzen darfst). Liefert je Treffer Name, Kurzbeschreibung und "
    "input_schema. Aufgerufen wird das Gefundene mit run_tool(name, args)."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Was du tun willst, in eigenen Worten (z. B. „Bild erzeugen“)."},
        "limit": {"type": "integer", "description": f"Höchstzahl Treffer (Standard {_DEFAULT_LIMIT}, höchstens {_MAX_LIMIT})."},
    },
    "required": ["query"],
}


def effective_tool_names(agent: dict, *, username: str, project: dict | None) -> list[str]:
    """Zentrale Freigabe (S6); lazy importiert, weil agents ↔ tools sich beim Start sonst im Kreis importieren."""
    from hydrahive.agents.effective_tools import effective_tool_names as _effective
    return _effective(agent, username=username, project=project)


def _agent_for(ctx: ToolContext) -> dict | None:
    from hydrahive.agents import config as agent_config
    return agent_config.get(ctx.agent_id)


def _project_for(ctx: ToolContext) -> dict | None:
    if not ctx.project_id:
        return None
    from hydrahive.projects import config as project_config
    return project_config.get(ctx.project_id)


def _allowed_for(ctx: ToolContext) -> set[str]:
    """Freigabe dieses Laufs; ohne bekannten Agenten nichts (fail-closed)."""
    agent = _agent_for(ctx)
    if not agent:
        return set()
    return set(effective_tool_names(agent, username=ctx.user_id, project=_project_for(ctx)))


async def _query_vector(query: str, store) -> list[float] | None:
    """Anfrage-Vektor nur, wenn Einträge Vektoren haben und ein Modell da ist; nie blockierend, nie ein Fehler."""
    if not store.vectors():
        return None
    try:
        from hydrahive.llm._config import load_config
        from hydrahive.llm.embed import aembed
        model = (load_config() or {}).get("embed_model") or ""
        if not model:
            return None
        return await asyncio.wait_for(aembed(query, model, embed_type="query"), timeout=3.0)
    except Exception:  # noqa: BLE001 — ohne Embedding bleibt es bei der Wortsuche (K9)
        logger.debug("find_tools: kein Anfrage-Vektor, nur Wortsuche", exc_info=True)
        return None


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.catalog import _store
    from hydrahive.catalog.index import rebuild_tool_index
    from hydrahive.catalog.search import search

    query = str((args or {}).get("query") or "").strip()
    if not query:
        return ToolResult.fail("Suchbegriff fehlt (query).")
    try:
        limit = int((args or {}).get("limit") or _DEFAULT_LIMIT)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    limit = max(1, min(limit, _MAX_LIMIT))

    rebuild_tool_index()                      # spiegelt die aktuelle Tool-Menge (entfernte Tools verschwinden, S7)
    store = _store.get_store()
    allowed = _allowed_for(ctx)
    vector = await _query_vector(query, store)
    found = search(query, allowed=allowed, kind="tool", limit=limit, query_vector=vector)
    results = [{"name": e.name, "description": e.title, "input_schema": e.schema or {"type": "object", "properties": {}}}
               for e in found]
    return ToolResult.ok({"results": results, "hint": _HINT})


TOOL = Tool(name="find_tools", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="catalog")
