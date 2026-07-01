"""Tests für die Server-Migrations-Endpoints (rsync Voll-Klon).

Verifiziert Input-Validierung, admin-only, Trigger-/Secret-Datei-Handling
(Passwort in separater 0600-Datei, NICHT im Klartext-Trigger) und Status/Log.
Es wird KEIN echtes rsync/ssh ausgeführt — nur der Router bis zur Trigger-Datei.
"""
from __future__ import annotations

import json
import stat

import pytest

from hydrahive.api.routes import migration as migration_mod
from hydrahive.settings import settings
from tests.conftest import error_code


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """data_dir auf ein Test-Tmp umlenken — NIE in die echte data_dir schreiben.

    Der Router löst die Marker-Pfade zur Laufzeit aus settings.data_dir auf,
    daher genügt der monkeypatch hier.
    """
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", d, raising=False)
    yield


def _body(**over):
    base = {
        "host": "192.168.178.121",
        "port": 22,
        "ssh_user": "root",
        "password": "s3cret-pass",
        "bwlimit_kbps": 0,
    }
    base.update(over)
    return base


def test_start_requires_admin(client, auth_headers):
    r = client.post("/api/admin/migration/start", json=_body(), headers=auth_headers)
    assert r.status_code == 403


def test_start_requires_auth(client):
    r = client.post("/api/admin/migration/start", json=_body())
    assert r.status_code in (401, 403)


def test_start_writes_trigger_and_secret(client, admin_headers):
    r = client.post("/api/admin/migration/start", json=_body(), headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"started": True}

    # Trigger enthält Host/Port/User — aber KEIN Passwort.
    assert migration_mod._trigger_path().exists()
    trigger = json.loads(migration_mod._trigger_path().read_text())
    assert trigger["host"] == "192.168.178.121"
    assert trigger["port"] == 22
    assert trigger["ssh_user"] == "root"
    assert "password" not in trigger
    assert "s3cret-pass" not in migration_mod._trigger_path().read_text()

    # Passwort steht in separater Secret-Datei mit Mode 0600.
    assert migration_mod._secret_path().exists()
    assert migration_mod._secret_path().read_text() == "s3cret-pass"
    mode = stat.S_IMODE(migration_mod._secret_path().stat().st_mode)
    assert mode == 0o600, f"Secret-Datei muss 0600 sein, ist {oct(mode)}"


def test_start_rejects_invalid_host(client, admin_headers):
    r = client.post("/api/admin/migration/start",
                    json=_body(host="bad host; rm -rf /"), headers=admin_headers)
    assert r.status_code == 400
    assert error_code(r) == "migration_invalid_host"
    assert not migration_mod._secret_path().exists()


def test_start_rejects_invalid_user(client, admin_headers):
    r = client.post("/api/admin/migration/start",
                    json=_body(ssh_user="root;evil"), headers=admin_headers)
    assert r.status_code == 400
    assert error_code(r) == "migration_invalid_user"


def test_start_rejects_empty_password(client, admin_headers):
    r = client.post("/api/admin/migration/start",
                    json=_body(password=""), headers=admin_headers)
    assert r.status_code == 422  # pydantic min_length


def test_start_conflict_when_running(client, admin_headers):
    r1 = client.post("/api/admin/migration/start", json=_body(), headers=admin_headers)
    assert r1.status_code == 200
    r2 = client.post("/api/admin/migration/start", json=_body(), headers=admin_headers)
    assert r2.status_code == 409
    assert error_code(r2) == "migration_already_running"


def test_status_reports_running(client, admin_headers):
    assert client.get("/api/admin/migration/status",
                      headers=admin_headers).json()["running"] is False
    client.post("/api/admin/migration/start", json=_body(), headers=admin_headers)
    assert client.get("/api/admin/migration/status",
                      headers=admin_headers).json()["running"] is True


def test_status_reports_last_result(client, admin_headers):
    migration_mod._done_path().write_text(json.dumps({"ok": True, "finished_at": 123}))
    st = client.get("/api/admin/migration/status", headers=admin_headers).json()
    assert st["running"] is False
    assert st["last_result"] == {"ok": True, "finished_at": 123}


def test_log_absent(client, admin_headers, tmp_path, monkeypatch):
    log = tmp_path / "migration.log"
    monkeypatch.setattr(settings, "migration_log_path", log, raising=False)
    r = client.get("/api/admin/migration/log", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["exists"] is False


def test_log_reads_tail(client, admin_headers, tmp_path, monkeypatch):
    log = tmp_path / "migration.log"
    log.write_text("line1\nline2\nline3\n")
    monkeypatch.setattr(settings, "migration_log_path", log, raising=False)
    r = client.get("/api/admin/migration/log?tail=2", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["exists"] is True
    assert data["lines"] == ["line2\n", "line3\n"]


def test_bwlimit_persisted_in_trigger(client, admin_headers):
    client.post("/api/admin/migration/start",
                json=_body(bwlimit_kbps=5000), headers=admin_headers)
    trigger = json.loads(migration_mod._trigger_path().read_text())
    assert trigger["bwlimit_kbps"] == 5000
