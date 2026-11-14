"""Gemeinsame Sicherheits-Bausteine der Projekt-Authoring-Tools.

Erzwingt: nur Projekt-Agenten dürfen authoren; erzeugte Spezialisten erben
höchstens die Tools ihres Erzeugers und nie die Authoring-Tools selbst."""
from __future__ import annotations

from hydrahive.tools.base import ToolContext

SPECIALIST_RUNTIME_SCHEMA: dict[str, dict] = {
    "fallback_models": {"type": "array", "items": {"type": "string"}},
    "reasoning_effort": {"type": "string"},
    "max_tokens": {"type": "integer", "minimum": 1, "maximum": 200_000},
    "max_iterations": {"type": "integer", "minimum": 1, "maximum": 250},
    "compact_model": {"type": "string"},
    "compact_tool_result_limit": {"type": "integer", "minimum": 100, "maximum": 50_000},
    "compact_reserve_tokens": {"type": "integer", "minimum": 1_000, "maximum": 100_000},
    "compact_threshold_pct": {"type": "integer", "minimum": 30, "maximum": 100},
    "compact_max_turns": {"type": "integer", "minimum": 1_000, "maximum": 100_000},
    "tool_result_max_chars": {"type": "integer", "minimum": 0, "maximum": 1_000_000},
    "cache_ttl": {"type": "string", "enum": ["5m", "1h"]},
    "handoff_timeout_seconds": {"type": "integer", "minimum": 30, "maximum": 3_600},
}
SPECIALIST_RUNTIME_FIELDS = tuple(SPECIALIST_RUNTIME_SCHEMA)

# Für Werkzeug-Schemas (Aufräumen 14.11.2026): nur noch Felder, die NICHT aus dem Agenten-Template kommen.
_TEMPLATE_OWNED = {"fallback_models", "reasoning_effort", "max_tokens", "max_iterations", "compact_model",
                   "compact_threshold_pct", "cache_ttl", "handoff_timeout_seconds"}
SPECIALIST_FREE_SCHEMA: dict[str, dict] = {k: v for k, v in SPECIALIST_RUNTIME_SCHEMA.items() if k not in _TEMPLATE_OWNED}

# Agenten-Templates (Spec agent-templates.md Kap. 5): Modell, Fallback und Budget kommen aus dem Template.
TEMPLATE_SCHEMA: dict[str, dict] = {"template": {"type": "string", "description": (
    "Agenten-Template (z. B. reviewer, backend, frontend, security, recherche, klein). Legt Modellkette und "
    "Budget fest; mit Template sind llm_model/fallback_models/max_* nicht einstellbar.")}}

AUTHORING_TOOLS: frozenset[str] = frozenset({
    "create_specialist", "configure_specialist", "list_specialists",
    "write_skill", "delete_skill",
})


class AuthoringError(Exception):
    """Aufrufer ist kein berechtigter Projekt-Agent."""


def resolve_project_agent(ctx: ToolContext) -> tuple[dict, str]:
    """Liefert (agent_cfg, project_id) wenn der Aufrufer ein Projekt-Agent mit
    project_id ist — sonst AuthoringError."""
    from hydrahive.agents import config as agent_config
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        raise AuthoringError("Agent nicht gefunden")
    if agent.get("type") != "project":
        raise AuthoringError("Nur Projekt-Agenten dürfen Spezialisten/Skills anlegen")
    pid = agent.get("project_id")
    if not pid:
        raise AuthoringError("Projekt-Agent ohne project_id")
    return agent, pid


def specialist_runtime_changes(args: dict) -> dict:
    """Return only explicitly requested, globally bounded runtime fields."""
    return {field: args[field] for field in SPECIALIST_RUNTIME_FIELDS if field in args}


def bounded_tools(requested: list[str], creator_tools: list[str]) -> list[str]:
    """Schnittmenge der angefragten Tools mit denen des Erzeugers, ohne die
    Authoring-Tools selbst (kein Spezialist erbt Authoring-Macht)."""
    creator = set(creator_tools)
    return [t for t in requested if t in creator and t not in AUTHORING_TOOLS]
