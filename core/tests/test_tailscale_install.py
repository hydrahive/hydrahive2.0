"""Tests für POST /api/tailscale/install (Paket 1: Install via UI).

Seit installer-core-first Teil 2 läuft die Installation über den Zusatz-Module-Runner (installer/addon-ctl.sh); der
Endpoint schreibt nur noch die Anfrage. Die Weiterleitung selbst prüft test_addon_legacy_routes.py.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def trigger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from hydrahive.api.routes import _addon_request
    path = tmp_path / ".addon_request"
    monkeypatch.setattr(_addon_request, "trigger_path", lambda: path)
    return path


def test_install_requires_auth(client):
    """POST /api/tailscale/install ohne Token → 401."""
    r = client.post("/api/tailscale/install")
    assert r.status_code == 401


def test_install_requires_admin(client, auth_headers, trigger):
    """POST /api/tailscale/install als non-admin User → 403."""
    r = client.post("/api/tailscale/install", headers=auth_headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "admin_only"
    assert not trigger.exists()


def test_install_returns_current_status(client, admin_headers, trigger):
    """Antwort bleibt kompatibel ({ok, rc, output, status}) und liefert den aktuellen Status mit."""
    async def fake_status():
        return {"installed": False, "connected": False, "backend_state": "NoState"}

    with patch("hydrahive.api.routes.tailscale.get_status", fake_status):
        r = client.post("/api/tailscale/install", headers=admin_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["rc"] == 0 and body["output"] == ""
    assert body["status"]["backend_state"] == "NoState"
