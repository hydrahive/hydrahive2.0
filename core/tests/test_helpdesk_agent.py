"""Hilfe-Assistent: Agent pro Nutzer (docs/plans/help-assistant.md, Etappe 1, Schritt 3).

- eigener Agent mit Marker is_help, eine feste Sitzung (wie Buddy)
- nur die Hilfe-Werkzeuge – nichts, was Dateien, Terminal, Web oder Gedächtnis anfasst
- Modell = Standard-Modell der LLM-Einstellungen; fehlt es, kein Agent, sondern model_missing (Fenster zeigt Hinweis)
- taucht nicht als Hauptagent und nicht in der Agentenliste auf
"""
from __future__ import annotations

import pytest

HELP_TOOLS = ["help_search", "help_read"]


@pytest.fixture(scope="module", autouse=True)
def _init_db(setup_test_env):
    from hydrahive.db import init_db

    init_db()


@pytest.fixture(autouse=True)
def _clean(setup_test_env, _init_db, monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk import _agent

    monkeypatch.setattr(_agent, "load_config", lambda: {"default_model": "claude-sonnet-4-6", "providers": []})

    def wipe():
        for a in agent_config.list_by_owner("testuser"):
            if a.get("is_help"):
                agent_config.delete(a["id"])
    wipe()
    yield
    wipe()


def test_creates_help_agent_once(setup_test_env):
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    first = get_or_create_help_agent("testuser")
    second = get_or_create_help_agent("testuser")
    assert first["created"] is True and second["created"] is False
    assert first["agent_id"] == second["agent_id"]
    assert first["session_id"] == second["session_id"]
    assert first["model_missing"] is False


def test_only_help_tools(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    agent = agent_config.get(get_or_create_help_agent("testuser")["agent_id"])
    assert agent["is_help"] is True
    assert sorted(agent["tools"]) == sorted(HELP_TOOLS)
    assert agent["mcp_servers"] == []
    assert agent["type"] == "specialist"


def test_tools_reset_if_changed(setup_test_env):
    """Jemand gibt dem Hilfe-Agenten von Hand mehr Werkzeuge → beim nächsten Abruf wieder nur die Hilfe-Werkzeuge."""
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    aid = get_or_create_help_agent("testuser")["agent_id"]
    agent_config.update(aid, tools=["shell_exec", "help_search"])
    get_or_create_help_agent("testuser")
    assert sorted(agent_config.get(aid)["tools"]) == sorted(HELP_TOOLS)


def test_uses_default_model(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    agent = agent_config.get(get_or_create_help_agent("testuser")["agent_id"])
    assert agent["llm_model"] == "claude-sonnet-4-6"


def test_no_default_model_no_agent(setup_test_env, monkeypatch):
    """Ohne Standard-Modell kein stiller Rückgriff auf ein fest eingebautes Modell (anders als Buddy)."""
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk._agent import get_or_create_help_agent
    from hydrahive.helpdesk import _agent

    monkeypatch.setattr(_agent, "load_config", lambda: {"default_model": "", "providers": []})
    state = get_or_create_help_agent("testuser")
    assert state == {"model_missing": True, "agent_id": None, "session_id": None, "created": False}
    assert not [a for a in agent_config.list_by_owner("testuser") if a.get("is_help")]


def test_follows_default_model_change(setup_test_env, monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk._agent import get_or_create_help_agent
    from hydrahive.helpdesk import _agent

    aid = get_or_create_help_agent("testuser")["agent_id"]
    monkeypatch.setattr(_agent, "load_config", lambda: {"default_model": "gpt-5", "providers": []})
    get_or_create_help_agent("testuser")
    assert agent_config.get(aid)["llm_model"] == "gpt-5"


def test_not_primary_agent(setup_test_env):
    from hydrahive.agents.primary import primary_agent_for
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    aid = get_or_create_help_agent("testuser")["agent_id"]
    primary = primary_agent_for("testuser")
    assert primary is None or primary["id"] != aid


def test_hidden_from_agent_list_api(setup_test_env):
    from hydrahive.api.routes import agents as agents_route
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    aid = get_or_create_help_agent("testuser")["agent_id"]
    listed = agents_route.list_agents(("testuser", "user"))
    assert aid not in [a["id"] for a in listed]
    listed_admin = agents_route.list_agents(("admin", "admin"))
    assert aid not in [a["id"] for a in listed_admin]


def test_other_users_get_own_agent(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.helpdesk._agent import get_or_create_help_agent

    a = get_or_create_help_agent("testuser")
    b = get_or_create_help_agent("zweiter")
    try:
        assert a["agent_id"] != b["agent_id"]
        assert agent_config.get(b["agent_id"])["owner"] == "zweiter"
    finally:
        agent_config.delete(b["agent_id"])
