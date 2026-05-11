"""Test dass Anthropic-OAuth-Headers die benötigten Beta-Features anfragen."""
from __future__ import annotations

from hydrahive.llm._anthropic import _OAUTH_HEADERS


def test_oauth_headers_enthaelt_anthropic_beta():
    assert "anthropic-beta" in _OAUTH_HEADERS


def test_anthropic_beta_enthaelt_prompt_caching():
    """prompt-caching-2024-07-31 ist die Grundvoraussetzung für cache_control."""
    beta = _OAUTH_HEADERS["anthropic-beta"]
    assert "prompt-caching-2024-07-31" in beta


def test_anthropic_beta_enthaelt_extended_cache_ttl():
    """extended-cache-ttl-2025-04-11: aktiviert ttl:"1h" — sonst nur 5m Default.

    Token-Audit-Fix: ohne diesen Header wurde unser _with_cache_breakpoint-Fix
    (ttl="1h") komplett ignoriert.
    """
    beta = _OAUTH_HEADERS["anthropic-beta"]
    assert "extended-cache-ttl-2025-04-11" in beta


def test_anthropic_beta_enthaelt_oauth_token_support():
    beta = _OAUTH_HEADERS["anthropic-beta"]
    assert "oauth-2025-04-20" in beta


def test_user_agent_und_x_app_gesetzt():
    """Anthropic-OAuth erkennt nur Claude-Code-CLI als legitimen Client."""
    assert _OAUTH_HEADERS["user-agent"].startswith("claude-cli/")
    assert _OAUTH_HEADERS["x-app"] == "cli"
