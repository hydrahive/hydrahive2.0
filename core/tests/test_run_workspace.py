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


# --- Testseite (ziele/projekt-testumgebung.md §3 Weg B, E1c) --------------------------------------------------------

def test_testseite_hinweis_mit_projekt_und_port(tmp_path, monkeypatch):
    monkeypatch.delenv("HH_PREVIEW_PORT_MIN", raising=False)
    monkeypatch.delenv("HH_PREVIEW_PORT_MAX", raising=False)
    hint = project_layout_hint(tmp_path, {"name": "P", "git_repos": {}, "preview_port": 18123})
    assert "Testseite:" in hint and "127.0.0.1" in hint and "$HH_PREVIEW_PORT" in hint
    assert "18123" in hint and "‚Testseite öffnen‘" in hint and "Blocker" in hint


def test_testseite_hinweis_ohne_vergebenen_port_nennt_die_variable(tmp_path):
    from hydrahive.runner._run_workspace import preview_hint
    project = {"name": "P", "git_repos": {}}
    hint = preview_hint(project)
    assert "für dieses Projekt $HH_PREVIEW_PORT" in hint
    assert "preview_port" not in project                                   # nichts vergeben, nichts geschrieben


def test_testseite_hinweis_nicht_im_container_modus(tmp_path):
    project = {"name": "P", "git_repos": {}, "preview_port": 18123,
               "execution": {"mode": "container", "container": "hh-p1", "workdir": "/work", "user": 1000}}
    assert "Testseite:" not in project_layout_hint(tmp_path, project)


def test_testseite_hinweis_nicht_bei_kaputter_ausfuehrung(tmp_path):
    project = {"name": "P", "git_repos": {}, "execution": {"mode": "irgendwas"}}
    assert "Testseite:" not in project_layout_hint(tmp_path, project)


def test_testseite_hinweis_nur_mit_projekt(monkeypatch):
    """Ohne Projekt baut der Runner den Projekt-Block gar nicht (runner.py: nur wenn active_project_id + Konfig)."""
    import inspect

    from hydrahive.runner import runner
    src = inspect.getsource(runner)
    block = src[src.index("_proj = None"):src.index("local_tools = effective_tool_names(")]   # Anker: erste Zeile nach dem Projekt-Block
    assert "if active_project_id:" in block and "if _proj:" in block and "project_layout_hint(" in block
