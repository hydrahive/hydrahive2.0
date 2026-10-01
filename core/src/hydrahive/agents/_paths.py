from __future__ import annotations

import re
from pathlib import Path

from hydrahive.settings import settings


def workspace_for(agent: dict) -> Path:
    """Auto-derive the workspace path for an agent. HydraHive owns it.

    Caller never accepts a free-form path from the user — pattern enforces
    that every agent's filesystem ops happen inside `data/workspaces/`.
    """
    agent_type = agent.get("type", "specialist")
    agent_id = agent["id"]
    base = settings.data_dir / "workspaces"

    if agent_type == "master":
        return base / "master" / agent_id
    if agent_type == "project":
        project_id = agent.get("project_id") or agent_id
        return base / "projects" / project_id
    return base / "specialists" / agent_id


def ensure_workspace(agent: dict) -> Path:
    """Create the workspace dir if it doesn't exist. Returns the resolved path."""
    ws = workspace_for(agent)
    ws.mkdir(parents=True, exist_ok=True)
    return ws.resolve()


# Agent-IDs sind UUIDs bzw. einfache Kennungen. Alles andere (/, \\, ..,
# Leerzeichen) wäre ein Pfad und könnte agents_dir verlassen
# (Sicherheitsprüfung 01.10.2026: fremde config.json aus einem Workspace).
_AGENT_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


def is_valid_agent_id(agent_id: object) -> bool:
    return isinstance(agent_id, str) and _AGENT_ID.fullmatch(agent_id) is not None


def agent_dir(agent_id: str) -> Path:
    """Ordner des Agenten — ValueError bei allem, was keine Agent-ID ist."""
    if not is_valid_agent_id(agent_id):
        raise ValueError(f"Ungültige Agent-ID: {agent_id!r}")
    return settings.agents_dir / agent_id


def system_prompt_path(agent_id: str) -> Path:
    return agent_dir(agent_id) / "system_prompt.md"


def config_path(agent_id: str) -> Path:
    return agent_dir(agent_id) / "config.json"


def soul_dir(agent_id: str) -> Path:
    return agent_dir(agent_id) / "soul"


def soul_file(agent_id: str, component: str) -> Path:
    return soul_dir(agent_id) / f"{component}.md"
