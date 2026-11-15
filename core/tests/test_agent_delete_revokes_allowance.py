"""Agent löschen entfernt die ID aus allowed_specialists aller Projekte — sonst bleibt eine tote
Freigabe stehen (Review PR #722, Fund 15.11.2026). Betrifft jeden Lösch-Weg über agent_config.delete
(= agents/_delete.py:delete — die Stelle, die den Agentenordner wirklich entfernt)."""
from __future__ import annotations


def _project(name: str) -> dict:
    from hydrahive.db.connection import init_db
    from hydrahive.projects import config as project_config
    init_db()
    return project_config.create(name=name, llm_model="claude-sonnet-4-6", created_by="testuser",
                                 members=["testuser"])


def _specialist(name: str) -> dict:
    from hydrahive.agents import config as agent_config
    return agent_config.create(agent_type="specialist", name=name, llm_model="claude-sonnet-4-6", tools=[],
                               owner="testuser", temperature=0.7, max_tokens=1000, thinking_budget=0)


def test_delete_removes_dead_id_from_allowed_specialists(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    spec = _specialist("Helfer")
    proj = _project("mit-freigabe")
    project_config.update(proj["id"], allowed_specialists=[spec["id"]])

    assert agent_config.delete(spec["id"]) is True

    reloaded = project_config.get(proj["id"])
    assert spec["id"] not in reloaded["allowed_specialists"]


def test_delete_leaves_other_ids_in_allowed_specialists(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    spec_a, spec_b = _specialist("A"), _specialist("B")
    proj = _project("mit-zwei")
    project_config.update(proj["id"], allowed_specialists=[spec_a["id"], spec_b["id"]])

    agent_config.delete(spec_a["id"])

    reloaded = project_config.get(proj["id"])
    assert reloaded["allowed_specialists"] == [spec_b["id"]]


def test_delete_removes_from_several_projects_at_once(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    spec = _specialist("Shared")
    p1, p2 = _project("eins"), _project("zwei")
    project_config.update(p1["id"], allowed_specialists=[spec["id"]])
    project_config.update(p2["id"], allowed_specialists=[spec["id"]])

    agent_config.delete(spec["id"])

    assert spec["id"] not in project_config.get(p1["id"])["allowed_specialists"]
    assert spec["id"] not in project_config.get(p2["id"])["allowed_specialists"]


def test_delete_without_any_allowance_does_nothing(setup_test_env):
    from hydrahive.agents import config as agent_config
    spec = _specialist("Unbenutzt")
    assert agent_config.delete(spec["id"]) is True
