from __future__ import annotations

import pytest

from hydrahive.agents import _validation
from hydrahive.agents._validation import AgentValidationError


def test_empty_model_rejected():
    with pytest.raises(AgentValidationError):
        _validation.validate_model("")


def test_passes_through_when_no_available_list(monkeypatch):
    monkeypatch.setattr(_validation, "_available_models", lambda: [])
    _validation.validate_model("openrouter/whatever:free")  # darf NICHT raisen


def test_accepts_model_in_available(monkeypatch):
    monkeypatch.setattr(_validation, "_available_models", lambda: ["openrouter/x", "claude-sonnet-4-6"])
    _validation.validate_model("claude-sonnet-4-6")


def test_rejects_unknown_when_list_present(monkeypatch):
    monkeypatch.setattr(_validation, "_available_models", lambda: ["openrouter/x"])
    with pytest.raises(AgentValidationError):
        _validation.validate_model("totally-made-up")
