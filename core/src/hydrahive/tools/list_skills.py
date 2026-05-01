from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Listet alle für diesen Agent verfügbaren Skills mit Name, Beschreibung "
    "und when_to_use. Nutze `load_skill(name)` um den Body eines Skills in "
    "den aktuellen Kontext zu laden."
)

_SCHEMA = {"type": "object", "properties": {}, "required": []}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.skills import list_for_agent
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        return ToolResult.fail("Agent nicht gefunden")
    owner = agent.get("owner") or ctx.user_id
    disabled = list(agent.get("disabled_skills", []))
    skills = list_for_agent(ctx.agent_id, owner, disabled=disabled)
    return ToolResult.ok({
        "skills": [{
            "name": s.name,
            "description": s.description,
            "when_to_use": s.when_to_use,
            "scope": s.scope,
            "tools_required": list(s.tools_required),
        } for s in skills],
        "count": len(skills),
    })


TOOL = Tool(
    name="list_skills",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="agents",
)
