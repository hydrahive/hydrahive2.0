"""Wählt das Arbeitsverzeichnis (cwd) für einen Run.

Hat die Session ein gültiges Projekt, ist das Projekt-Workspace das cwd — so
arbeitet der Agent (Buddy/Master) direkt im Projekt-Repo statt in seinem
generischen Agent-Workspace. Das ist der Grund, warum der Master sonst „sucht":
ohne aktives Projekt kennt er kein eindeutiges Arbeitsverzeichnis.

Konservativ: nur `session.project_id` weist das Projekt-Workspace zu. Der
tool_config-Pfad (Agent-zu-Agent-Runs) bleibt unverändert beim Agent-Workspace.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.agents._paths import ensure_workspace as _agent_workspace


def resolve_run_context(session, agent: dict, tool_config: dict | None = None) -> tuple[Path, str | None]:
    """Liefert (workspace, project_id) für den Run."""
    project_id = getattr(session, "project_id", None)
    if project_id:
        from hydrahive.projects import config as project_config
        from hydrahive.projects._paths import ensure_workspace as project_workspace

        if project_config.get(project_id):
            return project_workspace(project_id), project_id

    return _agent_workspace(agent), (tool_config or {}).get("project_id")
