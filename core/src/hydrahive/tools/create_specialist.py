"""create_specialist — Projekt-Agent legt einen projekt-gebundenen Spezialisten an."""
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, bounded_tools, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Legt einen neuen Spezialisten in DEINEM Projekt an (du musst Projekt-Agent sein). "
    "Der Spezialist erbt höchstens deine eigenen Tools und wird automatisch für die "
    "Delegation per ask_agent freigegeben."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Name des Spezialisten"},
        "description": {"type": "string", "description": "Wofür er zuständig ist"},
        "llm_model": {"type": "string", "description": "Optional; Default: dein eigenes Modell"},
        "tools": {"type": "array", "items": {"type": "string"},
                  "description": "Optional; Teilmenge deiner Tools. Default: Spezialist-Standard."},
    },
    "required": ["name"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._defaults import (
        DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_THINKING_BUDGET, DEFAULT_TOOLS,
    )
    from hydrahive.projects import config as project_config
    try:
        creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    name = (args.get("name") or "").strip()
    if not name:
        return ToolResult.fail("name fehlt")

    requested = args.get("tools")
    tools = bounded_tools(requested, creator.get("tools", [])) if requested else list(DEFAULT_TOOLS["specialist"])
    model = (args.get("llm_model") or creator.get("llm_model") or "").strip()

    try:
        cfg = agent_config.create(
            agent_type="specialist",
            name=name,
            llm_model=model,
            tools=tools,
            owner=creator.get("owner"),
            created_by=creator.get("id"),
            description=args.get("description", ""),
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
            thinking_budget=DEFAULT_THINKING_BUDGET,
            project_id=pid,
        )
    except Exception as e:
        return ToolResult.fail(f"Anlegen fehlgeschlagen: {e}")

    proj = project_config.get(pid)
    allowed = list((proj or {}).get("allowed_specialists", []))
    if cfg["id"] not in allowed:
        project_config.update(pid, allowed_specialists=allowed + [cfg["id"]])

    return ToolResult.ok({"id": cfg["id"], "name": name, "tools": tools, "project_id": pid})


TOOL = Tool(name="create_specialist", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
