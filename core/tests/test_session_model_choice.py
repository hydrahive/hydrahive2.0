"""Sitzungsmodell im Chat (Entscheidung Till 14.11.2026, Option B).

Projekt-/Spezialisten-Agent mit Template: nur Modelle der Kette. Buddy: frei. Ungebunden: frei.
"""
from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents._session_models import allowed_session_models
from hydrahive.agents.templates import _store
from hydrahive.db import sessions as sessions_db
from hydrahive.runner._run_settings import chain_with_override, run_settings

KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "claude-fable-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}
PM = ["claude-opus-5-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"]


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch, client):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    yield
    _store.reset_cache()


@pytest.fixture
def agent():
    made = []

    def make(template=None, buddy=False, owner="testuser"):
        a = agent_config.create(agent_type="project" if template == "projekt-master" else "master",
                                name=f"sm-{len(made)}", llm_model="claude-sonnet-5", owner=owner, created_by=owner,
                                temperature=0.7, max_tokens=1000, thinking_budget=0, template=template)
        if buddy:
            agent_config.update(a["id"], is_buddy=True)
        made.append(a["id"])
        return agent_config.get(a["id"])
    yield make
    for aid in made:
        agent_config.delete(aid)


def test_erlaubte_modelle(agent):
    assert allowed_session_models(agent("projekt-master")) == PM
    assert allowed_session_models(agent("buddy", buddy=True)) is None
    assert allowed_session_models(agent(None)) is None


def test_route_lehnt_fremdes_modell_ab(client, auth_headers, agent):
    a = agent("projekt-master")
    s = sessions_db.create(agent_id=a["id"], user_id="testuser", title="x")
    r = client.patch(f"/api/sessions/{s.id}", json={"model_override": "claude-fable-5"}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "model_not_in_template"
    r = client.patch(f"/api/sessions/{s.id}", json={"model_override": "openai-codex/gpt-5.6-terra"},
                     headers=auth_headers)
    assert r.status_code == 200
    r = client.patch(f"/api/sessions/{s.id}", json={"model_override": ""}, headers=auth_headers)
    assert r.status_code == 200


def test_buddy_frei(client, auth_headers, agent):
    a = agent("buddy", buddy=True)
    s = sessions_db.create(agent_id=a["id"], user_id="testuser", title="x")
    r = client.patch(f"/api/sessions/{s.id}", json={"model_override": "claude-fable-5"}, headers=auth_headers)
    assert r.status_code == 200


def test_alter_fremder_override_wird_ignoriert(agent):
    rs = run_settings(agent("projekt-master"))
    assert chain_with_override(rs, "claude-fable-5") == (PM[0], PM[1:])
    assert chain_with_override(rs, PM[1]) == (PM[1], [PM[0], PM[2]])


def test_buddy_override_frei_vor_kette(agent):
    rs = run_settings(agent("buddy", buddy=True))
    first, rest = chain_with_override(rs, "claude-fable-5")
    assert first == "claude-fable-5" and "claude-sonnet-5" in rest


def test_sessions_api_liefert_erlaubte_modelle(client, auth_headers, agent):
    a = agent("projekt-master")
    r = client.get(f"/api/agents/{a['id']}/session-models", headers=auth_headers)
    assert r.status_code == 200 and r.json() == {"restricted": True, "models": PM}
    b = agent(None)
    assert client.get(f"/api/agents/{b['id']}/session-models", headers=auth_headers).json()["restricted"] is False
