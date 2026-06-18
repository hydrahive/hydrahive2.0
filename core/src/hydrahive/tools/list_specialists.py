"""list_specialists — Spezialisten des eigenen Projekts auflisten."""
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = "Listet die Spezialisten deines Projekts (id, name, tools, status)."
_SCHEMA = {"type": "object", "properties": {}, "required": []}

_PROMPT_HINT = (
    "\n\nDu kannst dein Projekt selbst gestalten: lege mit `create_specialist` "
    "Spezialisten an, gib ihnen mit `write_skill` (Projekt-Bibliothek) Fähigkeiten, "
    "sieh sie mit `list_specialists` und delegiere via `ask_agent`."
)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    try:
        _creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))
    out = [
        {"id": a["id"], "name": a.get("name", ""), "tools": a.get("tools", []),
         "status": a.get("status", "active")}
        for a in agent_config.list_all()
        if a.get("type") == "specialist" and a.get("project_id") == pid
    ]
    return ToolResult.ok({"specialists": out, "count": len(out)})


TOOL = Tool(name="list_specialists", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents", prompt_hint=_PROMPT_HINT)
