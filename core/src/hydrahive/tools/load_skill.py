from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Lädt den vollen Body eines Skills in die Konversation. Skills sind "
    "wiederverwendbare Anweisungs-Templates (z.B. 'code-review', "
    "'git-workflow'). Mit `list_skills` siehst du was verfügbar ist."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Skill-Name (siehe list_skills)"},
    },
    "required": ["name"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.skills import list_for_agent
    name = (args.get("name") or "").strip()
    if not name:
        return ToolResult.fail("Kein Skill-Name angegeben")
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        return ToolResult.fail("Agent nicht gefunden")
    owner = agent.get("owner") or ctx.user_id
    disabled = list(agent.get("disabled_skills", []))
    skills = list_for_agent(ctx.agent_id, owner, disabled=disabled)
    skill = next((s for s in skills if s.name == name), None)
    if not skill:
        available = ", ".join(s.name for s in skills) or "(keine)"
        return ToolResult.fail(f"Skill '{name}' nicht gefunden. Verfügbar: {available}")
    return ToolResult.ok({
        "name": skill.name,
        "description": skill.description,
        "when_to_use": skill.when_to_use,
        "tools_required": list(skill.tools_required),
        "sources": [{"url": s.url, "auth": s.auth, "description": s.description}
                    for s in skill.sources],
        "body": skill.body,
        "scope": skill.scope,
    })


TOOL = Tool(
    name="load_skill",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="agents",
)
