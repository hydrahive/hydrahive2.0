"""Projekt-bewusste Workspace-Auflösung für einen Run.

Hat die Session ein gültiges Projekt, ist das Projekt-Workspace das cwd —
so arbeitet Buddy/Master direkt im Projekt-Repo statt im generischen
Agent-Workspace (der Grund, warum der Master sonst „sucht").
"""
from __future__ import annotations

from types import SimpleNamespace

from hydrahive.runner._run_workspace import project_layout_hint, resolve_run_context


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


def test_project_layout_hint_describes_repo_and_assets(tmp_path):
    (tmp_path / "ProjektX" / ".git").mkdir(parents=True)
    (tmp_path / "media").mkdir()
    (tmp_path / ".scripts").mkdir()
    (tmp_path / ".git").mkdir()  # Root-Repo-Metadaten — darf NICHT als Eintrag erscheinen
    project = {"name": "ProjektX", "git_repos": {"ProjektX": {}, "_root": {}}}

    hint = project_layout_hint(tmp_path, project)

    assert "Aktives Projekt: ProjektX" in hint
    assert str(tmp_path) in hint
    assert "./ProjektX/ (Git-Repo)" in hint
    assert "./media/" in hint
    assert "./.scripts/" in hint
    assert "  - ./.git/" not in hint
    assert "cd ./ProjektX/" in hint


def test_project_layout_hint_multi_repo_no_single_cd(tmp_path):
    (tmp_path / "repo-a" / ".git").mkdir(parents=True)
    (tmp_path / "repo-b" / ".git").mkdir(parents=True)
    project = {"name": "Multi", "git_repos": {"repo-a": {}, "repo-b": {}}}

    hint = project_layout_hint(tmp_path, project)

    assert "./repo-a/ (Git-Repo)" in hint
    assert "./repo-b/ (Git-Repo)" in hint
    assert "cd ./" not in hint  # bei mehreren Repos kein Einzel-cd-Hinweis


def test_bogus_project_falls_back_to_agent_workspace(monkeypatch):
    from hydrahive.agents import _paths as ap
    from hydrahive.projects import config as pc

    monkeypatch.setattr(pc, "get", lambda pid: None)
    session = SimpleNamespace(project_id="ghost")

    ws, pid = resolve_run_context(session, _agent(), None)

    assert pid is None
    assert ws == ap.workspace_for(_agent())
