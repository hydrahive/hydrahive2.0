"""Tests for the per-workstation verify_tls toggle (Federation).

Covers three layers:
  1. DB layer  — create/update/_row default
  2. API layer — POST/PUT round-trip via TestClient
  3. Registry layer — httpx receives the right verify= value

Why these tests matter: getting verify_tls wrong silently breaks
the federation handshake. A self-signed Tailnet peer needs verify=0;
a public CA peer needs verify=1. We want both code paths covered
so future refactors can't regress on either.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1) DB layer
# ---------------------------------------------------------------------------

def test_create_defaults_verify_tls_to_true(client):
    """create_workstation() without verify_tls should default to True."""
    from hydrahive.db import federation as fed_db

    ws = fed_db.create_workstation(
        name="db-default-test", url="https://example.invalid"
    )
    try:
        assert ws["verify_tls"] == 1  # SQLite stores as int
    finally:
        fed_db.delete_workstation(ws["id"])


def test_create_with_verify_tls_false(client):
    """Explicit verify_tls=False is persisted."""
    from hydrahive.db import federation as fed_db

    ws = fed_db.create_workstation(
        name="db-self-signed-test",
        url="https://100.127.0.1:8100",
        verify_tls=False,
    )
    try:
        assert ws["verify_tls"] == 0
    finally:
        fed_db.delete_workstation(ws["id"])


def test_update_can_toggle_verify_tls(client):
    """update_workstation() respects verify_tls in the allow-list."""
    from hydrahive.db import federation as fed_db

    ws = fed_db.create_workstation(
        name="db-toggle-test", url="https://x.invalid", verify_tls=True
    )
    try:
        updated = fed_db.update_workstation(ws["id"], verify_tls=False)
        assert updated["verify_tls"] == 0

        # Flip back
        updated = fed_db.update_workstation(ws["id"], verify_tls=True)
        assert updated["verify_tls"] == 1
    finally:
        fed_db.delete_workstation(ws["id"])


def test_update_ignores_unknown_fields(client):
    """The allow-list still blocks arbitrary column writes."""
    from hydrahive.db import federation as fed_db

    ws = fed_db.create_workstation(
        name="db-allowlist-test", url="https://x.invalid"
    )
    try:
        # 'id' shouldn't be writable. Should just no-op silently.
        updated = fed_db.update_workstation(ws["id"], id="hacked")
        assert updated["id"] == ws["id"]
    finally:
        fed_db.delete_workstation(ws["id"])


# ---------------------------------------------------------------------------
# 2) API layer
# ---------------------------------------------------------------------------

def test_api_create_workstation_with_verify_tls(client, admin_headers):
    """POST /api/federation/workstations accepts and returns verify_tls."""
    resp = client.post(
        "/api/federation/workstations",
        headers=admin_headers,
        json={
            "name": "api-test-self-signed",
            "url": "https://100.127.195.68:8100",
            "token": "test-token",
            "verify_tls": False,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["verify_tls"] is False
    assert data["has_token"] is True
    # Token must NOT leak back.
    assert "token" not in data
    # Cleanup
    client.delete(f"/api/federation/workstations/{data['id']}", headers=admin_headers)


def test_api_update_workstation_verify_tls(client, admin_headers):
    """PUT can toggle verify_tls in isolation."""
    create = client.post(
        "/api/federation/workstations",
        headers=admin_headers,
        json={"name": "api-toggle", "url": "https://x.invalid"},
    )
    ws_id = create.json()["id"]
    assert create.json()["verify_tls"] is True  # default

    try:
        resp = client.put(
            f"/api/federation/workstations/{ws_id}",
            headers=admin_headers,
            json={"verify_tls": False},
        )
        assert resp.status_code == 200
        assert resp.json()["verify_tls"] is False
    finally:
        client.delete(f"/api/federation/workstations/{ws_id}", headers=admin_headers)


def test_api_list_includes_verify_tls(client, admin_headers):
    """GET /workstations exposes verify_tls in every row."""
    create = client.post(
        "/api/federation/workstations",
        headers=admin_headers,
        json={"name": "api-list-test", "url": "https://x.invalid", "verify_tls": False},
    )
    ws_id = create.json()["id"]
    try:
        resp = client.get("/api/federation/workstations", headers=admin_headers)
        assert resp.status_code == 200
        rows = resp.json()
        match = [r for r in rows if r["id"] == ws_id]
        assert len(match) == 1
        assert match[0]["verify_tls"] is False
    finally:
        client.delete(f"/api/federation/workstations/{ws_id}", headers=admin_headers)


def test_api_create_requires_admin(client, auth_headers):
    """Non-admin users cannot create workstations."""
    resp = client.post(
        "/api/federation/workstations",
        headers=auth_headers,
        json={"name": "x", "url": "https://x.invalid"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3) Registry layer — httpx must receive the correct verify=
# ---------------------------------------------------------------------------


def _make_fake_client_class(captured: list, response_payload: dict):
    """Builds a stand-in for httpx.AsyncClient that records the verify= kwarg
    and returns a canned JSON response. Used to assert that the registry
    threads verify_tls all the way through to the HTTP layer.
    """
    from unittest.mock import MagicMock

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs.get("verify"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=response_payload)
            return resp

        async def post(self, url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=response_payload)
            return resp

    return _FakeClient


def test_fetch_card_passes_verify_false_for_self_signed(client):
    """When verify_tls=0 on the row, AsyncClient is built with verify=False."""
    import asyncio
    from hydrahive.db import federation as fed_db
    from hydrahive.federation import registry

    ws = fed_db.create_workstation(
        name="reg-self-signed",
        url="https://100.127.0.1:8100",
        verify_tls=False,
    )
    try:
        registry._card_cache.pop(ws["id"], None)
        captured: list = []
        FakeClient = _make_fake_client_class(captured, {"name": "fake-card"})

        with patch("hydrahive.federation.registry.httpx.AsyncClient", FakeClient):
            card = asyncio.run(registry.fetch_card(ws["id"], force=True))

        assert card == {"name": "fake-card"}
        assert captured == [False]
    finally:
        fed_db.delete_workstation(ws["id"])


def test_fetch_card_passes_verify_true_by_default(client):
    """A workstation created with default settings gets verify=True."""
    import asyncio
    from hydrahive.db import federation as fed_db
    from hydrahive.federation import registry

    ws = fed_db.create_workstation(name="reg-public", url="https://example.com")
    try:
        registry._card_cache.pop(ws["id"], None)
        captured: list = []
        FakeClient = _make_fake_client_class(captured, {"name": "fake"})

        with patch("hydrahive.federation.registry.httpx.AsyncClient", FakeClient):
            asyncio.run(registry.fetch_card(ws["id"], force=True))

        assert captured == [True]
    finally:
        fed_db.delete_workstation(ws["id"])


def test_remote_chat_honours_verify_flag(client):
    """remote_chat() must read verify_tls from the same DB row."""
    import asyncio
    from hydrahive.db import federation as fed_db
    from hydrahive.federation import registry

    ws = fed_db.create_workstation(
        name="reg-chat-self-signed",
        url="https://100.127.0.1:8100",
        token="t",
        verify_tls=False,
    )
    try:
        captured: list = []
        FakeClient = _make_fake_client_class(captured, {"text": "hello"})

        with patch("hydrahive.federation.registry.httpx.AsyncClient", FakeClient):
            text = asyncio.run(registry.remote_chat(ws["id"], "hi"))

        assert text == "hello"
        assert captured == [False]
    finally:
        fed_db.delete_workstation(ws["id"])
