"""Gemeinsame Sicherheits-Bausteine der Projekt-Authoring-Tools.

Erzwingt: nur Projekt-Agenten dürfen authoren; erzeugte Spezialisten erben
höchstens die Tools ihres Erzeugers und nie die Authoring-Tools selbst."""
from __future__ import annotations

from hydrahive.tools.base import ToolContext

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


def bounded_tools(requested: list[str], creator_tools: list[str]) -> list[str]:
    """Schnittmenge der angefragten Tools mit denen des Erzeugers, ohne die
    Authoring-Tools selbst (kein Spezialist erbt Authoring-Macht)."""
    creator = set(creator_tools)
    return [t for t in requested if t in creator and t not in AUTHORING_TOOLS]
