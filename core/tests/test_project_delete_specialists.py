"""Projekt löschen räumt alle Agenten des Projekts weg – auch Spezialisten (create_specialist, Storyteller-Helfer).

Vorher wurde nur der Projekt-Agent gelöscht; Spezialisten mit ``project_id`` blieben verwaist liegen.
"""
from __future__ import annotations


def _project(name: str) -> dict:
    from hydrahive.db.connection import init_db
    from hydrahive.projects import config as project_config
    init_db()  # Migrationen (delete() räumt VM-/Container-/Mount-Zuweisungen auf)
    return project_config.create(name=name, llm_model="claude-sonnet-4-6", created_by="testuser", members=["testuser"])


def _specialist(project_id: str | None, name: str) -> dict:
    from hydrahive.agents import config as agent_config
    return agent_config.create(agent_type="specialist", name=name, llm_model="claude-sonnet-4-6", tools=[],
                               owner="testuser", temperature=0.7, max_tokens=1000, thinking_budget=0,
                               project_id=project_id)


def test_delete_removes_project_specialists(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    proj = _project("mit-helfern")
    helpers = [_specialist(proj["id"], f"Helfer {i}") for i in range(3)]

    assert project_config.delete(proj["id"]) is True

    assert agent_config.get(proj["agent_id"]) is None
    for h in helpers:
        assert agent_config.get(h["id"]) is None


def test_delete_keeps_agents_of_other_projects_and_unbound(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    gone, other = _project("weg"), _project("bleibt")
    own = _specialist(gone["id"], "eigener")
    foreign = _specialist(other["id"], "fremder")
    free = _specialist(None, "ohne Projekt")

    project_config.delete(gone["id"])

    assert agent_config.get(own["id"]) is None
    assert agent_config.get(foreign["id"]) is not None
    assert agent_config.get(free["id"]) is not None
    assert agent_config.get(other["agent_id"]) is not None

