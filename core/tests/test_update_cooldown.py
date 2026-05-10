"""Cooldown auf POST /api/system/update (5min).

Bug-Kontext: ohne Cooldown löste Click-Spam mehrere parallele update.sh-Runs
aus, weil der systemd-Path-Watcher bei jedem write von .update_request
triggert. Außerdem war im Frontend ein 15s-Stable-Done-Fallback drin
(commit 2818a6d), der das Modal nach 15s als "fertig" markierte, obwohl
update.sh noch 3-8min lief — User klickte dann nochmal in dem Glauben,
dass nichts passiert war.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def _reset_cooldown():
    """Cooldown-State zwischen Tests resetten."""
    from hydrahive.api.routes import system_admin
    system_admin._last_update_trigger = 0.0


def test_update_requires_admin(client, auth_headers):
    _reset_cooldown()
    r = client.post("/api/system/update", headers=auth_headers)
    assert r.status_code == 403


def test_update_requires_auth(client):
    _reset_cooldown()
    r = client.post("/api/system/update")
    assert r.status_code == 401


def test_update_first_call_succeeds(client, admin_headers, tmp_path, monkeypatch):
    _reset_cooldown()
    # UPDATE_SCRIPT muss existieren — auf ein Test-File mappen
    fake_script = tmp_path / "update.sh"
    fake_script.write_text("#!/bin/sh\necho fake")
    fake_trigger = tmp_path / ".update_request"
    monkeypatch.setattr("hydrahive.api.routes.system_admin.UPDATE_SCRIPT", fake_script)
    monkeypatch.setattr("hydrahive.api.routes.system_admin.UPDATE_TRIGGER", fake_trigger)

    r = client.post("/api/system/update", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["started"] is True
    assert fake_trigger.exists()


def test_update_second_call_blocked_by_cooldown(client, admin_headers, tmp_path, monkeypatch):
    """Innerhalb 5min nach erstem Klick: 429 mit update_cooldown_active."""
    _reset_cooldown()
    fake_script = tmp_path / "update.sh"
    fake_script.write_text("#!/bin/sh")
    fake_trigger = tmp_path / ".update_request"
    monkeypatch.setattr("hydrahive.api.routes.system_admin.UPDATE_SCRIPT", fake_script)
    monkeypatch.setattr("hydrahive.api.routes.system_admin.UPDATE_TRIGGER", fake_trigger)

    r1 = client.post("/api/system/update", headers=admin_headers)
    assert r1.status_code == 200

    r2 = client.post("/api/system/update", headers=admin_headers)
    assert r2.status_code == 429
    assert r2.json()["detail"]["code"] == "update_cooldown_active"


def test_update_after_cooldown_succeeds(client, admin_headers, tmp_path, monkeypatch):
    """Nach Ablauf des Cooldowns geht's wieder. Wir simulieren das via Zeit-Mock."""
    _reset_cooldown()
    fake_script = tmp_path / "update.sh"
    fake_script.write_text("#!/bin/sh")
    fake_trigger = tmp_path / ".update_request"
    monkeypatch.setattr("hydrahive.api.routes.system_admin.UPDATE_SCRIPT", fake_script)
    monkeypatch.setattr("hydrahive.api.routes.system_admin.UPDATE_TRIGGER", fake_trigger)

    # Setze last_trigger 301s in die Vergangenheit (Cooldown ist 300s)
    from hydrahive.api.routes import system_admin
    import time
    system_admin._last_update_trigger = time.time() - 301

    r = client.post("/api/system/update", headers=admin_headers)
    assert r.status_code == 200


def test_update_missing_script_returns_503(client, admin_headers, monkeypatch):
    _reset_cooldown()
    monkeypatch.setattr(
        "hydrahive.api.routes.system_admin.UPDATE_SCRIPT", Path("/nonexistent/update.sh"),
    )
    r = client.post("/api/system/update", headers=admin_headers)
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "update_script_missing"
