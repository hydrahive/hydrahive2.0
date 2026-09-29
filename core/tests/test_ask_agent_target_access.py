"""ask_agent darf nur Agenten beauftragen, die der Besitzer des Laufs nutzen darf.

Befund 29.09.2026 (Task 26841785): Die Zielsuche lief über ALLE Agenten aller
Nutzer (ID, Name, Teilstring), geprüft wurde nur bei Projekt-Agenten mit
Spezialisten-Liste. Der Handoff läuft aber als Besitzer des ZIEL-Agenten, also
mit dessen Werkzeugen, Gedächtnis und Freigaben.

Regel:
- Admin: alle Agenten
- sonst nur eigene Agenten (owner == Besitzer des Laufs)
Strenger als POST /api/sessions (#461): Dort läuft die Session als der
anfragende Nutzer. Ein Handoff läuft dagegen als Besitzer des Ziel-Agenten.
Ein Projekt-Mitglied, das den Admin-eigenen Projekt-Spezialisten beauftragt,
bekäme so dessen Zugangsdaten. Deshalb hier kein Projekt-Team-Zugang.
Namen und Teilstrings werden nur unter den erlaubten Agenten aufgelöst und
müssen eindeutig sein.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.agents import config as agent_config
from hydrahive.projects import config as project_config
from hydrahive.tools import ToolContext
from hydrahive.tools import ask_agent


def _agent(name: str, owner: str, agent_type: str = "specialist") -> dict:
    return agent_config.create(
        agent_type=agent_type, name=name, llm_model="m", owner=owner,
        temperature=0.7, max_tokens=1024, thinking_budget=0,
    )


@pytest.fixture
def made(client):
    created: list[dict] = []

    def make(name: str, owner: str, agent_type: str = "specialist") -> dict:
        a = _agent(name, owner, agent_type)
        created.append(a)
        return a

    yield make
    for a in created:
        agent_config.delete(a["id"])


@pytest.fixture
def posted(monkeypatch):
    """Fängt den Handoff ab: kein Netz, sofortige Antwort 'done'."""
    calls: list[State] = []

    async def fake_post_state(state: State) -> State:
        calls.append(state)
        return State(id=f"st-{len(calls)}", agent_id=state.agent_id, task=state.task)

    def fake_register_pending(state_id: str, expected: str = ""):
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(State(agent_id="x", task=TaskBlock(type="feature", description="ok", status="done")))
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(ask_agent, "post_state", fake_post_state)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    return calls


def _run(target: str, user: str, tmp_path, *, caller: str = "test-agent-user", project_id=None):
    ctx = ToolContext(session_id="s", agent_id=caller, user_id=user, workspace=tmp_path, project_id=project_id)
    return asyncio.run(ask_agent._execute({"agent_id": target, "task": "hilf mir"}, ctx))


def _targets(calls: list[State]) -> list[str]:
    return [c.handoff.reason.split("|", 1)[0].removeprefix("hh-target:") for c in calls]


# --- fremde Agenten -------------------------------------------------------

def test_foreign_agent_by_id_is_refused_without_handoff(made, posted, tmp_path):
    foreign = made("Fremder Buddy", "admin", "master")
    res = _run(foreign["id"], "testuser", tmp_path)
    assert res.success is False and "Zugriff" in (res.error or "")
    assert posted == []


def test_foreign_agent_by_exact_name_is_refused(made, posted, tmp_path):
    made("Fremder Buddy", "admin", "master")
    res = _run("fremder buddy", "testuser", tmp_path)
    assert res.success is False
    assert posted == []


def test_substring_never_resolves_to_foreign_agent(made, posted, tmp_path):
    foreign = made("Geheimer Werkzeugkasten", "admin")
    _run("werkzeugkasten", "testuser", tmp_path)
    assert foreign["id"] not in _targets(posted)


# --- erlaubte Ziele -------------------------------------------------------

def test_own_agent_by_id_is_allowed(made, posted, tmp_path):
    own = made("Mein Helfer", "testuser")
    res = _run(own["id"], "testuser", tmp_path)
    assert res.success is True, res.error
    assert _targets(posted) == [own["id"]]


def test_own_agent_by_exact_name_is_allowed(made, posted, tmp_path):
    own = made("Mein Helfer", "testuser")
    assert _run("MEIN HELFER", "testuser", tmp_path).success is True
    assert _targets(posted) == [own["id"]]


def test_unique_substring_among_own_agents_is_allowed(made, posted, tmp_path):
    made("Fremder Rechercheur", "admin")
    own = made("Mein Rechercheur", "testuser")
    assert _run("rechercheur", "testuser", tmp_path).success is True
    assert _targets(posted) == [own["id"]]


def test_ambiguous_name_is_refused_with_choices(made, posted, tmp_path):
    a = made("Doppelt", "testuser")
    b = made("Doppelt", "testuser")
    res = _run("doppelt", "testuser", tmp_path)
    assert res.success is False and "mehrdeutig" in (res.error or "")
    assert a["id"] in res.error and b["id"] in res.error
    assert posted == []


def test_admin_may_use_any_agent(made, posted, tmp_path):
    other = made("Nutzer-Helfer", "testuser")
    assert _run(other["id"], "admin", tmp_path, caller="test-agent-001").success is True
    assert _targets(posted) == [other["id"]]


def test_unknown_run_owner_is_refused(made, posted, tmp_path):
    own = made("Waise", "gibt-es-nicht")
    res = _run(own["id"], "gibt-es-nicht", tmp_path)
    assert res.success is False and posted == []


# --- Projekt-Kontext ------------------------------------------------------

@pytest.fixture
def team_project(client, made):
    spec = made("Team-Spezialist", "admin")
    proj = project_config.create(
        name="AskTeam", llm_model="m", created_by="admin",
        members=[{"username": "testuser", "role": "write"}],
    )
    proj = project_config.update(proj["id"], allowed_specialists=[spec["id"]])
    yield proj, spec
    project_config.delete(proj["id"])


def test_project_member_may_not_delegate_to_foreign_owned_team(team_project, posted, tmp_path):
    """Der Handoff liefe als Besitzer des Spezialisten (hier admin)."""
    proj, spec = team_project
    assert _run(spec["id"], "testuser", tmp_path, project_id=proj["id"]).success is False
    assert _run(proj["agent_id"], "testuser", tmp_path, project_id=proj["id"]).success is False
    assert posted == []


def test_own_agent_still_allowed_in_project_context(team_project, made, posted, tmp_path):
    proj, _spec = team_project
    own = made("Mein Helfer", "testuser")
    assert _run(own["id"], "testuser", tmp_path, project_id=proj["id"]).success is True
    assert _targets(posted) == [own["id"]]


def test_project_member_may_not_use_other_admin_specialist(team_project, made, posted, tmp_path):
    proj, _spec = team_project
    other = made("Nicht im Team", "admin")
    assert _run(other["id"], "testuser", tmp_path, project_id=proj["id"]).success is False
    assert posted == []


def test_project_agent_keeps_specialist_allowlist(team_project, made, posted, tmp_path):
    """Bestehende Regel bleibt: Ein Projekt-Agent mit Spezialisten-Liste darf
    nur diese beauftragen, auch wenn der Besitzer mehr dürfte (hier: Admin)."""
    proj, spec = team_project
    other = made("Admin-Eigener", "admin")
    res = _run(other["id"], "admin", tmp_path, caller=proj["agent_id"], project_id=proj["id"])
    assert res.success is False and "nicht freigegeben" in (res.error or "")
    assert _run(spec["id"], "admin", tmp_path, caller=proj["agent_id"], project_id=proj["id"]).success is True
