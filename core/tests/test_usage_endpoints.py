"""Tests: OpenRouter-Credits + Codex-Usage Normalisierung.

Gemockte HTTP-Responses — kein Netzwerk. Prüft die Parsing-Logik und das
'available: False'-Verhalten (fehlender Key/OAuth), das die UI zum Ausblenden
der jeweiligen Zeile nutzt.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from hydrahive.llm import _codex_usage, _openrouter_credits


def _fake_response(status_code: int, json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body)
    return resp


def _fake_client_ctx(resp: MagicMock) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _reset_caches() -> None:
    _openrouter_credits._cache = {"data": None, "fetched_at": 0.0}
    _codex_usage._cache = {"data": None, "fetched_at": 0.0}


# ---------- OpenRouter ----------

def test_openrouter_credits_computes_remaining_and_pct():
    _reset_caches()
    resp = _fake_response(200, {"data": {"total_credits": 100, "total_usage": 81.32}})
    with patch.object(_openrouter_credits, "openrouter_key", return_value="sk-or-test"), \
         patch("httpx.AsyncClient", return_value=_fake_client_ctx(resp)):
        out = asyncio.run(_openrouter_credits.fetch_credits())
    assert out["available"] is True
    assert out["total"] == 100
    assert out["used"] == 81.32
    assert out["remaining"] == 18.68
    assert out["used_pct"] == 81.3


def test_openrouter_credits_no_key_is_unavailable():
    _reset_caches()
    with patch.object(_openrouter_credits, "openrouter_key", return_value=""):
        out = asyncio.run(_openrouter_credits.fetch_credits())
    assert out["available"] is False
    assert out["reason"] == "no_api_key"


def test_openrouter_credits_401_invalid_key():
    _reset_caches()
    resp = _fake_response(401, {})
    with patch.object(_openrouter_credits, "openrouter_key", return_value="sk-bad"), \
         patch("httpx.AsyncClient", return_value=_fake_client_ctx(resp)):
        out = asyncio.run(_openrouter_credits.fetch_credits())
    assert out["available"] is False
    assert out["reason"] == "invalid_api_key"


def test_openrouter_credits_zero_total_no_div_by_zero():
    _reset_caches()
    resp = _fake_response(200, {"data": {"total_credits": 0, "total_usage": 0}})
    with patch.object(_openrouter_credits, "openrouter_key", return_value="sk-or-test"), \
         patch("httpx.AsyncClient", return_value=_fake_client_ctx(resp)):
        out = asyncio.run(_openrouter_credits.fetch_credits())
    assert out["available"] is True
    assert out["used_pct"] == 0.0
    assert out["remaining"] == 0


# ---------- Codex ----------

_CODEX_OK = {
    "plan_type": "prolite",
    "rate_limit": {
        "primary_window": {"used_percent": 47, "limit_window_seconds": 18000, "reset_after_seconds": 6189},
        "secondary_window": {"used_percent": 21, "limit_window_seconds": 604800, "reset_after_seconds": 556542},
    },
    "credits": {"has_credits": False, "unlimited": False, "balance": "0"},
}


def test_codex_usage_normalizes_windows():
    _reset_caches()
    resp = _fake_response(200, _CODEX_OK)
    with patch("hydrahive.oauth.openai_codex.resolve_openai_codex_token",
               AsyncMock(return_value={"access": "tok", "account_id": "acc"})), \
         patch("httpx.AsyncClient", return_value=_fake_client_ctx(resp)):
        out = asyncio.run(_codex_usage.fetch_usage())
    assert out["available"] is True
    assert out["plan_type"] == "prolite"
    assert out["primary"]["used_pct"] == 47.0
    assert out["primary"]["reset_in_s"] == 6189
    assert out["secondary"]["used_pct"] == 21.0
    assert out["credits"]["has_credits"] is False


def test_codex_usage_no_oauth_is_unavailable():
    _reset_caches()
    with patch("hydrahive.oauth.openai_codex.resolve_openai_codex_token",
               AsyncMock(return_value={"access": "", "account_id": ""})):
        out = asyncio.run(_codex_usage.fetch_usage())
    assert out["available"] is False
    assert out["reason"] == "no_oauth"


def test_codex_usage_403_unauthorized():
    _reset_caches()
    resp = _fake_response(403, {})
    with patch("hydrahive.oauth.openai_codex.resolve_openai_codex_token",
               AsyncMock(return_value={"access": "tok", "account_id": "acc"})), \
         patch("httpx.AsyncClient", return_value=_fake_client_ctx(resp)):
        out = asyncio.run(_codex_usage.fetch_usage())
    assert out["available"] is False
    assert out["reason"] == "unauthorized"
