import pytest
from hydrahive.agents import _validation
from hydrahive.agents._validation import AgentValidationError


def test_validate_uses_registry_known(monkeypatch):
    from hydrahive.llm import registry
    monkeypatch.setattr(registry, "known_ids", lambda: {"claude-sonnet-4-5", "openrouter/x"})
    _validation.validate_model("claude-sonnet-4-5")          # darf NICHT raisen (Fallback-claude)
    with pytest.raises(AgentValidationError):
        _validation.validate_model("nope/unknown")


def test_validate_failopen_empty_registry(monkeypatch):
    from hydrahive.llm import registry
    monkeypatch.setattr(registry, "known_ids", lambda: set())
    _validation.validate_model("anything-at-all")            # leer → durchwinken
