"""Tests für buddy/commands.py: set_model + list_models auf Live-Quelle."""
from __future__ import annotations

import pytest

from hydrahive.buddy import commands


def test_set_model_passes_through_when_cache_empty(monkeypatch):
    """Bei leerem Live-Cache darf set_model NICHT mit 'Unbekanntes Modell' ablehnen."""
    from hydrahive.agents import _validation
    monkeypatch.setattr(_validation, "_available_models", lambda: [])
    captured = {}
    monkeypatch.setattr(commands, "_require_buddy", lambda u: {"id": "b1", "llm_model": "x"})
    monkeypatch.setattr(commands.agent_config, "update", lambda aid, **kw: captured.update(kw))
    out = commands.set_model("user", "openrouter/deepseek/deepseek-v4-flash:free")
    assert out["ok"] is True
    assert captured["llm_model"] == "openrouter/deepseek/deepseek-v4-flash:free"


def test_set_model_empty_rejected():
    with pytest.raises(ValueError):
        commands.set_model("user", "  ")


def test_list_models_uses_live_cache(monkeypatch):
    """list_models gibt Live-Modelle zurück, nicht provider.models."""
    from hydrahive.agents import _validation
    monkeypatch.setattr(_validation, "_available_models", lambda: ["model-a", "model-b"])
    monkeypatch.setattr(commands, "_require_buddy", lambda u: {"id": "b1", "llm_model": "model-a"})
    out = commands.list_models("user")
    assert out["current"] == "model-a"
    assert "model-a" in out["available"]
    assert "model-b" in out["available"]
