"""Systemrollen-Templates werden nach llm.json gespiegelt (Aufräumen 14.11.2026)."""
from __future__ import annotations

import pytest

from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store
from hydrahive.llm import _config

KNOWN = {"claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    cfg = tmp_path / "llm.json"
    cfg.write_text('{"providers": [], "default_model": "alt-chat", "lessons_model": ""}')
    monkeypatch.setattr(type(_config.settings), "llm_config", property(lambda self: cfg), raising=False)
    _config._config_cache = None
    _store.reset_cache()
    yield
    _store.reset_cache()
    _config._config_cache = None


def _set_primary(tid, model):
    t = tpl.get(tid)
    tpl.save(tid, {**t, "chain": [model, *[m for m in t["chain"] if m != model]]}, by="admin")


def test_assistant_wird_chat_standard():
    _set_primary("assistant", "openai-codex/gpt-5.6-terra")
    assert _config.get_default("chat") == "openai-codex/gpt-5.6-terra"


def test_lehren_wird_lehren_modell():
    _set_primary("lehren", "MiniMax-M3.1-Flash")
    assert _config.get_default("lessons") == "MiniMax-M3.1-Flash"


def test_lehren_aus_bleibt_aus():
    _config.set_default("lessons", _config.LESSONS_OFF)
    _set_primary("lehren", "MiniMax-M3.1-Flash")
    assert _config.get_default("lessons") == _config.LESSONS_OFF


def test_andere_templates_spiegeln_nicht():
    _set_primary("reviewer", "openai-codex/gpt-5.6-terra")
    assert _config.get_default("chat") == "alt-chat"
