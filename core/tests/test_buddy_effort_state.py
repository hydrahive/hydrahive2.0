"""Buddy-Tiefe (Reasoning-Effort) überlebt das Neuladen der Seite.

Regression: Die Buddy-Seite hielt die gewählte Tiefe nur im React-State
(Start null → „Aus“). Gespeichert und wirksam war sie (session.metadata,
llm_calls zeigte xhigh/max), aber /api/buddy/state lieferte sie nicht mit.
Außerdem: „Neuer Chat“ verlor Tiefe und Modus der alten Session.
"""
from __future__ import annotations

import pytest

USER = "effort-state-user"


@pytest.fixture(autouse=True)
def _clean(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.db import init_db

    init_db()
    yield
    for a in agent_config.list_by_owner(USER):
        agent_config.delete(a["id"])


def test_state_liefert_session_tiefe_und_agent_standard():
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.db import sessions as sessions_db

    first = get_or_create_buddy(USER)
    assert first["reasoning_effort"] is None
    agent_config.update(first["agent_id"], reasoning_effort="high")
    sessions_db.set_reasoning_effort(first["session_id"], "max")
    state = get_or_create_buddy(USER)
    assert state["reasoning_effort"] == "max"
    assert state["default_reasoning_effort"] == "high"


def test_neuer_chat_uebernimmt_tiefe_und_modus():
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy.commands import clear_session
    from hydrahive.db import sessions as sessions_db

    first = get_or_create_buddy(USER)
    sessions_db.set_reasoning_effort(first["session_id"], "xhigh")
    sessions_db.set_buddy_mode(first["session_id"], "focus")
    new_id = clear_session(USER)["session_id"]
    md = sessions_db.get(new_id).metadata or {}
    assert md.get("reasoning_effort") == "xhigh"
    assert md.get("buddy_mode") == "focus"


def test_state_api_liefert_tiefe(client, auth_headers):
    from hydrahive.db import sessions as sessions_db

    sid = client.get("/api/buddy/state", headers=auth_headers).json()["session_id"]
    sessions_db.set_reasoning_effort(sid, "low")
    body = client.get("/api/buddy/state", headers=auth_headers).json()
    assert body["reasoning_effort"] == "low"


def test_buddy_seite_uebernimmt_tiefe_aus_dem_state():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "frontend/src/features/buddy/BuddyPage.tsx").read_text()
    assert "setReasoningEffort((s.reasoning_effort ?? null)" in src
    assert "agentDefault={state.default_reasoning_effort}" in src


def test_pill_zeigt_agent_standard_statt_aus():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "frontend/src/features/chat/ReasoningEffortPill.tsx").read_text()
    assert 'effort.default_label' in src and "agentDefault" in src
