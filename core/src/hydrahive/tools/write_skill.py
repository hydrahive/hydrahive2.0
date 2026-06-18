"""write_skill — Projekt-Agent legt Skills an/bearbeitet (Projekt-Bibliothek oder Spezialist)."""
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Legt einen Skill an oder bearbeitet ihn. Standard: Projekt-Bibliothek (alle "
    "Agenten deines Projekts sehen ihn). Mit `specialist_id` nur für genau diesen "
    "Spezialisten deines Projekts."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "kleinbuchstaben, a-z0-9_-"},
        "description": {"type": "string"},
        "when_to_use": {"type": "string"},
        "body": {"type": "string", "description": "Markdown-Anleitung"},
        "specialist_id": {"type": "string", "description": "Optional; Skill nur für diesen Spezialisten"},
    },
    "required": ["name", "description", "when_to_use", "body"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.skills import save_skill
    from hydrahive.skills.models import Skill
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

    ok, err = save_skill(Skill(
        name=(args.get("name") or "").strip(),
        description=args.get("description", ""),
        when_to_use=args.get("when_to_use", ""),
        body=args.get("body", ""),
        scope=scope, owner=owner,
    ))
    if not ok:
        return ToolResult.fail(f"Skill speichern fehlgeschlagen: {err}")
    return ToolResult.ok({"name": args["name"], "scope": scope})


TOOL = Tool(name="write_skill", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
