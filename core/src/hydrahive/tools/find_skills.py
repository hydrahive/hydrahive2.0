"""find_skills – passende Skills finden (Katalog, Spec S7/K6).

Durchsucht NUR die Skills, die ``skills.loader.list_for_agent`` für diesen Agenten liefert (System, eigener Nutzer, aktuelles
Projekt, eigener Agent, abzüglich abgeschalteter): nie Skills anderer Nutzer oder Projekte, und nie den Body. Den Inhalt
holt man danach mit ``load_skill(name)``. In der REGISTRY, aber in keiner Agenten-Config und keiner Standard-Liste.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_MAX_LIMIT = 10
_DEFAULT_LIMIT = 5
_HINT = "Inhalt mit load_skill(name) laden."

_DESCRIPTION = (
    "Sucht passende Skills (nur deine eigenen und die deines Projekts). Liefert je Treffer Name und Kurzbeschreibung. "
    "Den Inhalt lädst du mit load_skill(name)."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Was du tun willst, in eigenen Worten (z. B. „Fehler im Code suchen“)."},
        "limit": {"type": "integer", "description": f"Höchstzahl Treffer (Standard {_DEFAULT_LIMIT}, höchstens {_MAX_LIMIT})."},
    },
    "required": ["query"],
}


def _agent_for(ctx: ToolContext) -> dict | None:
    from hydrahive.agents import config as agent_config
    return agent_config.get(ctx.agent_id)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.catalog.index import build_skill_entries
    from hydrahive.catalog.search import bm25_rank, rrf

    query = str((args or {}).get("query") or "").strip()
    if not query:
        return ToolResult.fail("Suchbegriff fehlt (query).")
    try:
        limit = int((args or {}).get("limit") or _DEFAULT_LIMIT)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    limit = max(1, min(limit, _MAX_LIMIT))

    agent = _agent_for(ctx)
    if not agent:
        return ToolResult.ok({"results": [], "hint": _HINT})            # fail-closed: ohne Agent keine Skills
    entries = build_skill_entries(agent, user_id=ctx.user_id, project_id=ctx.project_id)   # NUR diese Menge wird gerankt
    found = rrf([bm25_rank(query, entries)], limit)
    from hydrahive.catalog import metrics
    metrics.record_search(ctx.session_id, "search_skills", query, [e.name for e in found])       # best effort, wirft nie
    return ToolResult.ok({"results": [{"name": e.name, "description": e.title, "scope": e.owner_scope} for e in found],
                          "hint": _HINT})


TOOL = Tool(name="find_skills", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="catalog")
