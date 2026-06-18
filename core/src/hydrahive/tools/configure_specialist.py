"""configure_specialist — Projekt-Agent ändert einen Spezialisten seines Projekts."""
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, bounded_tools, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Ändert einen Spezialisten DEINES Projekts (Modell, Tools, System-Prompt, "
    "Beschreibung, status aktiv/disabled). Tools werden auf deine eigenen begrenzt."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "agent_id": {"type": "string"},
        "llm_model": {"type": "string"},
        "tools": {"type": "array", "items": {"type": "string"}},
        "system_prompt": {"type": "string"},
        "description": {"type": "string"},
        "status": {"type": "string", "enum": ["active", "disabled"]},
    },
    "required": ["agent_id"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    try:
        creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    target_id = (args.get("agent_id") or "").strip()
    target = agent_config.get(target_id)
    if not target or target.get("type") != "specialist" or target.get("project_id") != pid:
        return ToolResult.fail("Spezialist nicht in deinem Projekt gefunden")

    changes: dict = {}
    if "llm_model" in args:
        changes["llm_model"] = args["llm_model"]
    if "tools" in args:
        changes["tools"] = bounded_tools(args["tools"], creator.get("tools", []))
    if "description" in args:
        changes["description"] = args["description"]
    if "status" in args:
        changes["status"] = args["status"]

    if changes:
        agent_config.update(target_id, **changes)
    if args.get("system_prompt"):
        agent_config.set_system_prompt(target_id, args["system_prompt"])

    updated = sorted([*changes, *(["system_prompt"] if args.get("system_prompt") else [])])
    return ToolResult.ok({"id": target_id, "updated": updated})


TOOL = Tool(name="configure_specialist", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
