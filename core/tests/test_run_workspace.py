"""Projekt-bewusste Workspace-Auflösung für einen Run.

Hat die Session ein gültiges Projekt, ist das Projekt-Workspace das cwd —
so arbeitet Buddy/Master direkt im Projekt-Repo statt im generischen
Agent-Workspace (der Grund, warum der Master sonst „sucht").
"""
from __future__ import annotations

from types import SimpleNamespace

from hydrahive.runner._run_workspace import resolve_run_context


def _agent() -> dict:
    return {"id": "agent-1", "name": "Master", "owner": "u1", "type": "master"}


def test_valid_session_project_assigns_project_workspace(monkeypatch):
    from hydrahive.projects import _paths as pp
    from hydrahive.projects import config as pc

    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "name": "ProjX"} if pid == "p1" else None)
    session = SimpleNamespace(project_id="p1")

    ws, pid = resolve_run_context(session, _agent(), None)

    assert pid == "p1"
    assert ws == pp.workspace_path("p1")


def test_no_project_uses_agent_workspace(monkeypatch):
    from hydrahive.agents import _paths as ap

    session = SimpleNamespace(project_id=None)

    ws, pid = resolve_run_context(session, _agent(), {"project_id": "tc-fallback"})

    assert pid == "tc-fallback"
    assert ws == ap.workspace_for(_agent())


def test_bogus_project_falls_back_to_agent_workspace(monkeypatch):
    from hydrahive.agents import _paths as ap
    from hydrahive.projects import config as pc

    monkeypatch.setattr(pc, "get", lambda pid: None)
    session = SimpleNamespace(project_id="ghost")

    ws, pid = resolve_run_context(session, _agent(), None)

    assert pid is None
    assert ws == ap.workspace_for(_agent())
