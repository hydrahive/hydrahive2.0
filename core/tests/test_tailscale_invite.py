"""Tests für Paket 2: Admin-Config + Invite (Tailscale-Pre-Auth-Keys via UI).

GET/PUT /api/tailscale/admin-config + POST /api/tailscale/invite.
Wichtige Eigenschaften die hier getestet werden:
- API-Key wird beim Schreiben gegen die Tailscale-API validiert
- API-Key wird NIE im GET-Response zurückgegeben
- Invite ohne Config → 400 (kein 500, klar erkennbarer Fehlercode)
- Auth + Admin-only auf allen 3 Routes
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Auth-Schutz (alle 3 Routes admin-only)
# ---------------------------------------------------------------------------

def test_admin_config_get_requires_auth(client):
    assert client.get("/api/tailscale/admin-config").status_code == 401


def test_admin_config_get_requires_admin(client, auth_headers):
    assert client.get("/api/tailscale/admin-config", headers=auth_headers).status_code == 403


def test_admin_config_put_requires_admin(client, auth_headers):
    r = client.put("/api/tailscale/admin-config", headers=auth_headers,
                   json={"api_key": "x", "tailnet": "-"})
    assert r.status_code == 403


def test_invite_requires_admin(client, auth_headers):
    assert client.post("/api/tailscale/invite", headers=auth_headers).status_code == 403


# ---------------------------------------------------------------------------
# Config-CRUD
# ---------------------------------------------------------------------------

def test_admin_config_get_default_unconfigured(client, admin_headers, tmp_path, monkeypatch):
    """Frische Installation: configured=false, kein Key im Response."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    # config_dir ist cached_property → Settings-Instanz neu laden
    from hydrahive import settings as s_mod
    s_mod.settings.__dict__.pop("config_dir", None)

    r = client.get("/api/tailscale/admin-config", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body == {"configured": False, "tailnet": "-"}
    assert "api_key" not in body


def test_admin_config_put_validates_key(client, admin_headers, tmp_path, monkeypatch):
    """PUT validiert Key gegen Tailscale-API. Bei Erfolg: gespeichert mit chmod 0600."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    from hydrahive import settings as s_mod
    s_mod.settings.__dict__.pop("config_dir", None)

    async def fake_validate(api_key, tailnet):
        return True, ""

    with patch("hydrahive.api.routes.tailscale.validate_api_key", fake_validate):
        r = client.put("/api/tailscale/admin-config", headers=admin_headers,
                       json={"api_key": "tskey-api-secret123", "tailnet": "-"})

    assert r.status_code == 200
    assert r.json() == {"configured": True, "tailnet": "-"}

    cfg_file = tmp_path / "tailscale-admin.json"
    assert cfg_file.exists()
    assert json.loads(cfg_file.read_text()) == {"api_key": "tskey-api-secret123", "tailnet": "-"}
    # chmod 0600 — niemand sonst darf den Key lesen
    assert (cfg_file.stat().st_mode & 0o777) == 0o600


def test_admin_config_put_rejects_invalid_key(client, admin_headers, tmp_path, monkeypatch):
    """PUT mit ungültigem Key → 400 + tailscale_admin_key_invalid, nichts gespeichert."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    from hydrahive import settings as s_mod
    s_mod.settings.__dict__.pop("config_dir", None)

    async def fake_validate(api_key, tailnet):
        return False, "HTTP 401"

    with patch("hydrahive.api.routes.tailscale.validate_api_key", fake_validate):
        r = client.put("/api/tailscale/admin-config", headers=admin_headers,
                       json={"api_key": "wrong", "tailnet": "-"})

    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "tailscale_admin_key_invalid"
    assert not (tmp_path / "tailscale-admin.json").exists()


def test_admin_config_get_never_returns_key(client, admin_headers, tmp_path, monkeypatch):
    """Auch nach gespeichertem Key bleibt der GET-Response ohne api_key-Feld."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    from hydrahive import settings as s_mod
    s_mod.settings.__dict__.pop("config_dir", None)

    (tmp_path / "tailscale-admin.json").write_text(
        json.dumps({"api_key": "secret-leak-test", "tailnet": "-"})
    )

    r = client.get("/api/tailscale/admin-config", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body == {"configured": True, "tailnet": "-"}
    # Defense-in-depth: nicht nur fehlt das Feld, der Wert taucht nirgends auf
    assert "secret-leak-test" not in r.text


# ---------------------------------------------------------------------------
# Invite-Endpoint
# ---------------------------------------------------------------------------

def test_invite_without_config_returns_400(client, admin_headers, tmp_path, monkeypatch):
    """Wenn kein API-Key hinterlegt → 400 mit klarem Code, nicht 500."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    from hydrahive import settings as s_mod
    s_mod.settings.__dict__.pop("config_dir", None)

    r = client.post("/api/tailscale/invite", headers=admin_headers)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "tailscale_admin_not_configured"


def test_invite_success_returns_authkey(client, admin_headers):
    """Mit Mock-API: Endpoint reicht key + expires aus Tailscale-Response durch."""
    async def fake_create():
        return {
            "auth_key": "tskey-auth-mockmockmockmock",
            "expires": "2026-05-11T10:00:00Z",
            "id": "k123",
        }

    with patch("hydrahive.api.routes.tailscale.create_invite", fake_create):
        r = client.post("/api/tailscale/invite", headers=admin_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["auth_key"].startswith("tskey-auth-")
    assert body["expires"]


def test_invite_api_failure_returns_502(client, admin_headers):
    """Tailscale-API-Fehler (HTTP 5xx, Netzwerk) → 502 Bad Gateway."""
    async def fake_create():
        raise RuntimeError("tailscale_api_unreachable")

    with patch("hydrahive.api.routes.tailscale.create_invite", fake_create):
        r = client.post("/api/tailscale/invite", headers=admin_headers)

    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "tailscale_api_unreachable"


# ---------------------------------------------------------------------------
# Admin-Modul direkt
# ---------------------------------------------------------------------------

def test_create_invite_sends_correct_payload(monkeypatch, tmp_path):
    """create_invite() schickt preauthorized=True + 24h-Expiry an die Tailscale-API."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    from hydrahive import settings as s_mod
    s_mod.settings.__dict__.pop("config_dir", None)

    (tmp_path / "tailscale-admin.json").write_text(
        json.dumps({"api_key": "tskey-api-test", "tailnet": "example.com"})
    )

    captured = {}
    def fake_api(path, api_key, *, method="GET", body=None, timeout=15):
        captured["path"] = path
        captured["method"] = method
        captured["body"] = json.loads(body.decode()) if body else None
        captured["api_key"] = api_key
        return {"key": "tskey-auth-generated", "expires": "2026-05-11T10:00:00Z", "id": "abc"}

    from hydrahive.tailscale import admin as admin_mod
    monkeypatch.setattr(admin_mod, "_ts_api_sync", fake_api)

    import asyncio
    result = asyncio.run(admin_mod.create_invite())

    assert result["auth_key"] == "tskey-auth-generated"
    assert captured["method"] == "POST"
    assert captured["path"] == "/tailnet/example.com/keys"
    assert captured["api_key"] == "tskey-api-test"
    assert captured["body"]["capabilities"]["devices"]["create"]["preauthorized"] is True
    assert captured["body"]["capabilities"]["devices"]["create"]["reusable"] is False
    assert captured["body"]["expirySeconds"] == 86400
