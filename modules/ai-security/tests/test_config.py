"""Konfigurations- und Allowlist-Grenzen."""
from __future__ import annotations

import pytest

from backend.config import ConfigError, configured_targets, validate_target


def test_exact_configured_origin_is_accepted():
    assert validate_target("http://127.0.0.1:11434") == "http://127.0.0.1:11434"


@pytest.mark.parametrize("value", [
    "http://127.0.0.1:11434/v1",
    "http://user:pass@127.0.0.1:11434",
    "http://127.0.0.1:11434?x=1",
    "https://127.0.0.1:11434",
    "http://127.0.0.1:11435",
])
def test_non_exact_origin_is_rejected(value):
    with pytest.raises(ConfigError):
        validate_target(value)


def test_invalid_operator_allowlist_fails_closed(monkeypatch):
    monkeypatch.setenv("HH_AI_SECURITY_TARGETS", "not-a-url")
    with pytest.raises(ConfigError):
        configured_targets()


def test_duplicate_targets_are_deduplicated(monkeypatch):
    monkeypatch.setenv(
        "HH_AI_SECURITY_TARGETS",
        "http://127.0.0.1:11434,http://127.0.0.1:11434/",
    )
    assert [target.origin for target in configured_targets()] == ["http://127.0.0.1:11434"]
