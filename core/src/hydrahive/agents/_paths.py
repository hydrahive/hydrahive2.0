from __future__ import annotations

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


def system_prompt_path(agent_id: str) -> Path:
    return settings.agents_dir / agent_id / "system_prompt.md"


def config_path(agent_id: str) -> Path:
    return settings.agents_dir / agent_id / "config.json"


def agent_dir(agent_id: str) -> Path:
    return settings.agents_dir / agent_id
