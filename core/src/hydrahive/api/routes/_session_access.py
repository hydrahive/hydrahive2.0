"""Gemeinsame Projekt- und Agent-Autorisierung für Session-Erzeuger."""
from __future__ import annotations

from fastapi import status

from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import config as project_config


def assert_project_access(project_id: str, username: str, role: str) -> dict:
    """Lädt ein Projekt und verlangt Schreibrecht für den Benutzer."""
    project = project_config.get(project_id)
    if not project:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, username, role, required="write")
    return project


def assert_agent_access(
    agent: dict, project: dict | None, username: str, role: str,
) -> None:
    """Erlaubt eigene/Admin-Agenten oder das Team des gebundenen Projekts."""
    if role == "admin" or agent.get("owner") == username:
        return
    if project is not None:
        team = {project.get("agent_id"), *(project.get("allowed_specialists") or [])}
        if agent.get("id") in team:
            return
    raise coded(status.HTTP_403_FORBIDDEN, "agent_no_access")
