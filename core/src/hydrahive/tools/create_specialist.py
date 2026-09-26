"""create_specialist — Projekt-Agent legt einen projekt-gebundenen Spezialisten an."""
from __future__ import annotations

from hydrahive.tools._project_authoring import (
    SPECIALIST_RUNTIME_SCHEMA,
    AuthoringError,
    bounded_tools,
    resolve_project_agent,
    specialist_runtime_changes,
)
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
        **SPECIALIST_RUNTIME_SCHEMA,
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
    desired_tools = requested if requested is not None else list(DEFAULT_TOOLS["specialist"])
    tools = bounded_tools(desired_tools, creator.get("tools", []))
    model = (args.get("llm_model") or creator.get("llm_model") or "").strip()
    runtime = specialist_runtime_changes(args)
    max_tokens = runtime.pop("max_tokens", DEFAULT_MAX_TOKENS)
    reasoning_effort = runtime.pop("reasoning_effort", "")
    fallback_models = runtime.pop("fallback_models", [])

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
            max_tokens=max_tokens,
            thinking_budget=DEFAULT_THINKING_BUDGET,
            reasoning_effort=reasoning_effort,
            fallback_models=fallback_models,
            project_id=pid,
            **runtime,
        )
    except Exception as e:
        return ToolResult.fail(f"Anlegen fehlgeschlagen: {e}")

    proj = project_config.get(pid)
    allowed = list((proj or {}).get("allowed_specialists", []))
    if cfg["id"] not in allowed:
        project_config.update(pid, allowed_specialists=allowed + [cfg["id"]])

    return ToolResult.ok({
        "id": cfg["id"], "name": name, "tools": tools, "project_id": pid,
        "max_iterations": cfg.get("max_iterations"),
        "max_tokens": cfg.get("max_tokens"),
        "handoff_timeout_seconds": cfg.get("handoff_timeout_seconds"),
    })


TOOL = Tool(name="create_specialist", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
