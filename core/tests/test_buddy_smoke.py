"""Smoke-Tests für den Buddy — Session-Lifecycle und Slash-Commands."""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module", autouse=True)
def _init_db(setup_test_env):
    from hydrahive.db import init_db
    init_db()


@pytest.fixture(autouse=True)
def _reset_buddy_agent(setup_test_env, _init_db):
    """Entfernt Buddy-Agents zwischen Tests damit get_or_create_buddy frisch startet."""
    from hydrahive.agents import config as agent_config
    for a in agent_config.list_by_owner("testuser"):
        if a.get("is_buddy"):
            agent_config.delete(a["id"])
    yield
    for a in agent_config.list_by_owner("testuser"):
        if a.get("is_buddy"):
            agent_config.delete(a["id"])


def test_get_or_create_buddy_creates_fresh(setup_test_env):
    from hydrahive.buddy import get_or_create_buddy

    result = get_or_create_buddy("testuser")

    assert result["created"] is True
    assert result["agent_id"]
    assert result["session_id"]
    assert result["agent_name"]


def test_get_or_create_buddy_idempotent(setup_test_env):
    from hydrahive.buddy import get_or_create_buddy

    first = get_or_create_buddy("testuser")
    second = get_or_create_buddy("testuser")

    assert second["created"] is False
    assert second["agent_id"] == first["agent_id"]


def test_clear_session_creates_new_session(setup_test_env):
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy.commands import clear_session

    initial = get_or_create_buddy("testuser")
    result = clear_session("testuser")

    assert result["ok"] is True
    assert result["session_id"] != initial["session_id"]


def test_remember_text_stores_note(setup_test_env):
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy.commands import remember
    from hydrahive.tools import _memory_store as memory

    info = get_or_create_buddy("testuser")
    result = remember("testuser", text="Lieblingsfarbe: blau", name="farbe")

    assert result["ok"] is True
    assert result["key"] == "farbe"
    stored = memory.read_key(info["agent_id"], "farbe")
    assert stored == "Lieblingsfarbe: blau"
