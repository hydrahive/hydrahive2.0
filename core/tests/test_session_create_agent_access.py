"""POST /api/sessions darf keine Session mit einem fremden Agenten anlegen.

Befund 27.09.2026 (Task 1b7e6d17): create_session prüfte nur, ob der Agent
existiert. Ein normaler Nutzer konnte so mit dem Buddy eines anderen Nutzers
arbeiten, weil check_owner danach nur den Session-Besitzer prüft.

Erlaubt bleibt:
- eigener Agent (owner == User)
- Admin mit jedem Agenten
- Agent eines Projekts (Projekt-Agent oder freigegebener Spezialist), wenn
  der User im Projekt mindestens write hat und die Session an dieses Projekt
  geheftet wird. So starten Projekt-Mitglieder weiter Sessions im Cockpit.
"""
from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.projects import config as project_config


def _agent(name: str, owner: str) -> dict:
    return agent_config.create(
        agent_type="specialist", name=name, llm_model="m", owner=owner,
        temperature=0.7, max_tokens=1024, thinking_budget=0,
    )


@pytest.fixture
def foreign_agent():
    a = _agent("Fremder", "admin")
    yield a
    agent_config.delete(a["id"])


@pytest.fixture
def own_agent():
    a = _agent("Meiner", "testuser")
    yield a
    agent_config.delete(a["id"])


def _post(client, headers, **body):
    return client.post("/api/sessions", json=body, headers=headers)


def test_foreign_agent_is_rejected(client, auth_headers, foreign_agent):
    r = _post(client, auth_headers, agent_id=foreign_agent["id"])
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "agent_no_access"


def test_own_agent_is_allowed(client, auth_headers, own_agent):
    r = _post(client, auth_headers, agent_id=own_agent["id"])
    assert r.status_code == 201, r.text


def test_admin_may_use_any_agent(client, admin_headers, own_agent):
    r = _post(client, admin_headers, agent_id=own_agent["id"])
    assert r.status_code == 201, r.text


def test_project_member_may_use_project_agent(client, auth_headers):
    proj = project_config.create(
        name="Team", llm_model="m", created_by="admin", members=["testuser"],
    )
    try:
        r = _post(client, auth_headers, agent_id=proj["agent_id"], project_id=proj["id"])
        assert r.status_code == 201, r.text
        assert r.json()["project_id"] == proj["id"]
    finally:
        project_config.delete(proj["id"])


def test_project_agent_needs_matching_project_in_request(client, auth_headers):
    """Ohne project_id gilt der Projekt-Agent als fremd: Die Session hätte
    sonst weder Workspace noch Skills des Projekts, aber den Agenten."""
    proj = project_config.create(
        name="Team2", llm_model="m", created_by="admin", members=["testuser"],
    )
    try:
        r = _post(client, auth_headers, agent_id=proj["agent_id"])
        assert r.status_code == 403, r.text
    finally:
        project_config.delete(proj["id"])


def test_allowed_specialist_of_project_is_ok(client, auth_headers, foreign_agent):
    proj = project_config.create(
        name="Team3", llm_model="m", created_by="admin", members=["testuser"],
    )
    try:
        project_config.update(proj["id"], allowed_specialists=[foreign_agent["id"]])
        r = _post(client, auth_headers, agent_id=foreign_agent["id"], project_id=proj["id"])
        assert r.status_code == 201, r.text
    finally:
        project_config.delete(proj["id"])


def test_foreign_agent_with_own_project_is_rejected(client, auth_headers, foreign_agent):
    """Ein eigenes Projekt macht einen fremden Agenten nicht zugänglich."""
    proj = project_config.create(name="Mein", llm_model="m", created_by="testuser")
    try:
        r = _post(client, auth_headers, agent_id=foreign_agent["id"], project_id=proj["id"])
        assert r.status_code == 403, r.text
    finally:
        project_config.delete(proj["id"])


def test_read_only_member_cannot_start_session(client, auth_headers):
    proj = project_config.create(
        name="Lesen", llm_model="m", created_by="admin", members=[{"username": "testuser", "role": "read"}],
    )
    try:
        r = _post(client, auth_headers, agent_id=proj["agent_id"], project_id=proj["id"])
        assert r.status_code == 403, r.text
    finally:
        project_config.delete(proj["id"])
