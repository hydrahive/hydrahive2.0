"""Tests für /api/llm/oauth — Codex (Regression) + Anthropic (neuer dritter Weg).

Kernpunkte:
- Beide Provider können start/exchange/revoke (Provider-Dispatch).
- Unbekannte Provider → 400.
- Anthropic-OAuth-Exchange löscht einen vorhandenen api_key NICHT (Koexistenz
  von Weg 1/2 [api_key/setup-token] mit Weg 3 [OAuth]).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch


def _fake_pkce():
    return ("verifier123", "challenge123")


def test_start_codex(client, admin_headers):
    with patch("hydrahive.api.routes.llm_oauth.openai_codex.make_pkce", _fake_pkce), \
         patch("hydrahive.api.routes.llm_oauth.openai_codex.make_state", lambda: "state-x"), \
         patch("hydrahive.api.routes.llm_oauth.openai_codex.authorize_url",
               lambda **k: "https://auth.openai.com/authorize?x=1"):
        r = client.post("/api/llm/oauth/start", json={"provider": "openai-codex"},
                        headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["authorize_url"].startswith("https://auth.openai.com/")


def test_start_anthropic(client, admin_headers):
    with patch("hydrahive.api.routes.llm_oauth.anthropic_oauth.make_pkce", _fake_pkce), \
         patch("hydrahive.api.routes.llm_oauth.anthropic_oauth.make_state", lambda: "state-y"), \
         patch("hydrahive.api.routes.llm_oauth.anthropic_oauth.authorize_url",
               lambda **k: "https://claude.ai/oauth/authorize?x=1"):
        r = client.post("/api/llm/oauth/start", json={"provider": "anthropic"},
                        headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["authorize_url"].startswith("https://claude.ai/oauth/authorize")


def test_start_unknown_provider_400(client, admin_headers):
    r = client.post("/api/llm/oauth/start", json={"provider": "groq"}, headers=admin_headers)
    assert r.status_code == 400


def test_start_requires_admin(client, auth_headers):
    r = client.post("/api/llm/oauth/start", json={"provider": "anthropic"}, headers=auth_headers)
    assert r.status_code in (401, 403)


def test_anthropic_exchange_preserves_api_key(client, admin_headers):
    """Weg 3 (OAuth) darf einen bestehenden api_key (Weg 1/2) NICHT löschen."""
    from hydrahive.settings import settings
    # Vorbedingung: Anthropic-Provider mit api_key existiert bereits.
    settings.llm_config.parent.mkdir(parents=True, exist_ok=True)
    settings.llm_config.write_text(json.dumps({
        "providers": [{"id": "anthropic", "name": "Anthropic",
                       "api_key": "sk-ant-api03-KEEPME", "models": ["claude-sonnet-4-6"]}],
        "default_model": "claude-sonnet-4-6", "embed_model": "",
    }))
    pending = {"provider": "anthropic", "verifier": "v", "state": "s", "ts": 9_999_999_999}

    token = {"access": "sk-ant-oat01-NEW", "refresh": "ref", "expires_at": 9_999_999_999, "scope": "x"}
    with patch("hydrahive.api.routes.llm_oauth._load_pending", return_value=pending), \
         patch("hydrahive.api.routes.llm_oauth._delete_pending"), \
         patch("hydrahive.api.routes.llm_oauth.anthropic_oauth.parse_callback_input",
               return_value={"code": "c", "state": "s"}), \
         patch("hydrahive.api.routes.llm_oauth.anthropic_oauth.exchange_code",
               new=AsyncMock(return_value=token)):
        r = client.post("/api/llm/oauth/exchange",
                        json={"provider": "anthropic", "code_or_url": "http://x/callback?code=c&state=s"},
                        headers=admin_headers)
    assert r.status_code == 200
    saved = json.loads(settings.llm_config.read_text())
    prov = next(p for p in saved["providers"] if p["id"] == "anthropic")
    assert prov["api_key"] == "sk-ant-api03-KEEPME"   # Weg 1/2 unangetastet
    assert prov["oauth"]["access"] == "sk-ant-oat01-NEW"  # Weg 3 dazu


def test_exchange_no_pending_400(client, admin_headers):
    with patch("hydrahive.api.routes.llm_oauth._load_pending", return_value={}):
        r = client.post("/api/llm/oauth/exchange",
                        json={"provider": "anthropic", "code_or_url": "code"},
                        headers=admin_headers)
    assert r.status_code == 400


def test_revoke_anthropic_keeps_api_key(client, admin_headers):
    from hydrahive.settings import settings
    settings.llm_config.parent.mkdir(parents=True, exist_ok=True)
    settings.llm_config.write_text(json.dumps({
        "providers": [{"id": "anthropic", "name": "Anthropic",
                       "api_key": "sk-ant-api03-KEEPME", "models": ["claude-sonnet-4-6"],
                       "oauth": {"access": "sk-ant-oat01-X"}}],
        "default_model": "claude-sonnet-4-6", "embed_model": "",
    }))
    r = client.delete("/api/llm/oauth/anthropic", headers=admin_headers)
    assert r.status_code == 200
    saved = json.loads(settings.llm_config.read_text())
    prov = next(p for p in saved["providers"] if p["id"] == "anthropic")
    assert "oauth" not in prov               # OAuth entfernt
    assert prov["api_key"] == "sk-ant-api03-KEEPME"  # api_key bleibt


def test_revoke_unknown_provider_400(client, admin_headers):
    r = client.delete("/api/llm/oauth/groq", headers=admin_headers)
    assert r.status_code == 400
