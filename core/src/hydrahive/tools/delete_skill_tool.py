"""delete_skill — Projekt-Agent löscht einen Skill seines Projekts."""
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Löscht einen Skill deines Projekts: Default Projekt-Bibliothek, mit "
    "`specialist_id` den Agent-Skill dieses Spezialisten."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "specialist_id": {"type": "string"},
    },
    "required": ["name"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.skills import delete_skill
    try:
        _creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    spec_id = (args.get("specialist_id") or "").strip()
    if spec_id:
        target = agent_config.get(spec_id)
        if not target or target.get("type") != "specialist" or target.get("project_id") != pid:
            return ToolResult.fail("Spezialist nicht in deinem Projekt gefunden")
        scope, owner = "agent", spec_id
    else:
        scope, owner = "project", pid

    if not delete_skill(scope, owner, (args.get("name") or "").strip()):
        return ToolResult.fail("Skill nicht gefunden")
    return ToolResult.ok({"deleted": args["name"], "scope": scope})


TOOL = Tool(name="delete_skill", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
