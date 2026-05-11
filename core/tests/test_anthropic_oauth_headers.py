"""Test dass Anthropic-OAuth-Headers die benötigten Beta-Features anfragen."""
from __future__ import annotations

from hydrahive.llm._anthropic import _OAUTH_HEADERS


def test_oauth_headers_enthaelt_anthropic_beta():
    assert "anthropic-beta" in _OAUTH_HEADERS


def test_anthropic_beta_enthaelt_prompt_caching():
    """prompt-caching-2024-07-31 ist die Grundvoraussetzung für cache_control."""
    beta = _OAUTH_HEADERS["anthropic-beta"]
    assert "prompt-caching-2024-07-31" in beta


def test_anthropic_beta_enthaelt_KEIN_extended_cache_ttl():
    """extended-cache-ttl wurde getestet (commit 0a648b3) und revertiert:
    Anthropic-Server-side Cache-Eviction passierte auch <5min, der 2×-
    Aufpreis für 1h-cache_creation wurde NICHT amortisiert.
    """
    beta = _OAUTH_HEADERS["anthropic-beta"]
    assert "extended-cache-ttl-2025-04-11" not in beta


def test_anthropic_beta_enthaelt_oauth_token_support():
    beta = _OAUTH_HEADERS["anthropic-beta"]
    assert "oauth-2025-04-20" in beta


def test_user_agent_und_x_app_gesetzt():
    """Anthropic-OAuth erkennt nur Claude-Code-CLI als legitimen Client."""
    assert _OAUTH_HEADERS["user-agent"].startswith("claude-cli/")
    assert _OAUTH_HEADERS["x-app"] == "cli"
