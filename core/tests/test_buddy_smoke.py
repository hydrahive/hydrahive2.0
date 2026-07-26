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


def test_buddy_config_exposes_full_safe_agent_settings(setup_test_env):
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy import _config as buddy_config

    info = get_or_create_buddy("testuser")
    cfg = buddy_config.get_config("testuser")

    assert cfg["agent_id"] == info["agent_id"]
    assert isinstance(cfg["available_tools"], list)
    assert all({"name", "description", "category"} <= set(tool) for tool in cfg["available_tools"])
    assert {
        "fallback_models",
        "temperature",
        "max_tokens",
        "thinking_budget",
        "reasoning_effort",
        "mcp_servers",
        "disabled_skills",
        "require_tool_confirm",
        "longterm_memory",
        "compact_tool_result_limit",
        "compact_reserve_tokens",
        "compact_max_turns",
        "max_iterations",
        "cache_ttl",
    } <= set(cfg)


def test_buddy_config_full_settings_roundtrip(setup_test_env):
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy import _config as buddy_config

    state = get_or_create_buddy("testuser")
    buddy_config.patch_config(
        "testuser",
        {
            "model": state["model"],
            "fallback_models": [],
            "temperature": 0.4,
            "max_tokens": 12_000,
            "thinking_budget": 2_000,
            "reasoning_effort": "medium",
            "mcp_servers": ["docs"],
            "disabled_skills": ["debugging"],
            "require_tool_confirm": True,
            "longterm_memory": False,
            "compact_tool_result_limit": 4_000,
            "compact_reserve_tokens": 8_000,
            "compact_max_turns": 2_000,
            "max_iterations": 12,
            "cache_ttl": "1h",
        },
    )

    cfg = buddy_config.get_config("testuser")
    assert cfg["model"] == state["model"]
    assert cfg["temperature"] == 0.4
    assert cfg["max_tokens"] == 12_000
    assert cfg["thinking_budget"] == 2_000
    assert cfg["reasoning_effort"] == "medium"
    assert cfg["mcp_servers"] == ["docs"]
    assert cfg["disabled_skills"] == ["debugging"]
    assert cfg["require_tool_confirm"] is True
    assert cfg["longterm_memory"] is False
    assert cfg["compact_tool_result_limit"] == 4_000
    assert cfg["compact_reserve_tokens"] == 8_000
    assert cfg["compact_max_turns"] == 2_000
    assert cfg["max_iterations"] == 12
    assert cfg["cache_ttl"] == "1h"

    buddy_config.patch_config("testuser", {"compact_max_turns": None})
    assert buddy_config.get_config("testuser")["compact_max_turns"] is None


def test_buddy_config_mail_roundtrip(setup_test_env):
    """Per-Buddy-Postfach: patch persistiert roh am Agent, get liefert maskiert."""
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy import _config as buddy_config

    get_or_create_buddy("testuser")
    buddy_config.patch_config(
        "testuser",
        {"tool_config": {"smtp": {"host": "w0.kas", "from": "a@b", "user": "u", "password": "longsecret123"}}},
    )

    cfg = buddy_config.get_config("testuser")
    assert cfg["tool_config"]["smtp"]["host"] == "w0.kas"
    assert cfg["tool_config"]["smtp"]["password"] == ""  # API maskiert
    assert cfg["tool_config"]["smtp"]["password_set"] is True
    # roh am Agent gespeichert
    raw = buddy_config._find_buddy("testuser")["tool_config"]["smtp"]["password"]
    assert raw == "longsecret123"
