"""API für Install/Entfernen der lokalen Bild-/Videogenerierung.

Die API stellt nur eine Anfrage (Trigger-Datei mit festem Wort). Ausgeführt
wird als root von hydrahive2-local-media.service über
installer/local-media-ctl.sh, nach dem Muster von Voice/Bridge.
"""
from __future__ import annotations

from pathlib import Path

import pytest


OK_STATUS = {
    "installed": False, "can_install": True, "can_uninstall": False, "blocked_reason": None,
    "gpu": {"name": "RTX 5060 Ti", "vram_mib": 16311}, "min_vram_mib": 12000,
    "free_bytes": 400 * 1024**3, "min_free_bytes": 40 * 1024**3, "download_bytes": 33 * 1024**3,
}


# Das Routen-Modul erst in den Fixtures importieren: Ein Import beim Sammeln
# der Tests hat früher settings.data_dir festgeschrieben, bevor conftest
# HH_DATA_DIR gesetzt hatte, und damit 53 fremde Tests rot gemacht.
@pytest.fixture
def route():
    from hydrahive.api.routes import system_local_media
    return system_local_media


@pytest.fixture
def log_file(tmp_path: Path, route, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "hydrahive2-local-media.log"
    monkeypatch.setattr(route, "_log_path", lambda: path)
    return path


@pytest.fixture
def trigger(tmp_path: Path, route, monkeypatch: pytest.MonkeyPatch, log_file: Path) -> Path:
    path = tmp_path / ".local_media_request"
    monkeypatch.setattr(route, "_trigger", lambda: path)
    return path


@pytest.fixture
def set_status(route, monkeypatch: pytest.MonkeyPatch):
    def _set(**changes: object) -> None:
        monkeypatch.setattr(route, "get_status", lambda: {**OK_STATUS, **changes})
    return _set


def test_status_requires_admin(client, auth_headers) -> None:
    assert client.get("/api/system/local-media/status", headers=auth_headers).status_code == 403


def test_install_requires_auth(client) -> None:
    assert client.post("/api/system/local-media/install").status_code == 401


def test_install_requires_admin(client, auth_headers, trigger: Path) -> None:
    assert client.post("/api/system/local-media/install", headers=auth_headers).status_code == 403
    assert not trigger.exists()


def test_status_returns_hardware_check(client, admin_headers, set_status, trigger) -> None:
    set_status()
    body = client.get("/api/system/local-media/status", headers=admin_headers).json()
    assert body["can_install"] is True
    assert body["running"] is False


def test_install_writes_fixed_word(client, admin_headers, set_status, trigger: Path) -> None:
    set_status()
    r = client.post("/api/system/local-media/install", headers=admin_headers)
    assert r.status_code == 200
    assert trigger.read_text() == "install"


def test_install_blocked_on_small_gpu(client, admin_headers, set_status, trigger: Path) -> None:
    set_status(can_install=False, blocked_reason="vram_too_small")
    r = client.post("/api/system/local-media/install", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "local_media_blocked"
    assert r.json()["detail"]["params"]["reason"] == "vram_too_small"
    assert not trigger.exists()


def test_uninstall_only_when_installed(client, admin_headers, set_status, trigger: Path) -> None:
    set_status()
    r = client.post("/api/system/local-media/uninstall", headers=admin_headers)
    assert r.status_code == 409
    assert not trigger.exists()


def test_uninstall_writes_fixed_word(client, admin_headers, set_status, trigger: Path) -> None:
    set_status(installed=True, can_install=False, can_uninstall=True)
    r = client.post("/api/system/local-media/uninstall", headers=admin_headers)
    assert r.status_code == 200
    assert trigger.read_text() == "uninstall"


def test_second_request_while_pending_is_rejected(client, admin_headers, set_status, trigger: Path) -> None:
    set_status()
    trigger.write_text("install")
    r = client.post("/api/system/local-media/install", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "local_media_busy"


def test_status_reports_pending_request(client, admin_headers, set_status, trigger: Path) -> None:
    set_status()
    trigger.write_text("uninstall")
    assert client.get("/api/system/local-media/status", headers=admin_headers).json()["running"] is True


def test_log_tail_is_capped(client, admin_headers, trigger: Path, log_file: Path) -> None:
    log_file.write_text("".join(f"zeile {i}\n" for i in range(3000)))
    body = client.get("/api/system/local-media/log?tail=99999", headers=admin_headers).json()
    assert body["exists"] is True
    assert len(body["lines"]) == 1000
    assert body["lines"][-1] == "zeile 2999\n"


def test_log_strips_terminal_colour_codes(client, admin_headers, trigger: Path, log_file: Path) -> None:
    # Die Installer-Skripte färben ihre Ausgabe. Roh im Dialog erschien das als "[1;36m".
    log_file.write_text("\x1b[1;36m[hh2-media]\x1b[0m Container entfernen\n")
    body = client.get("/api/system/local-media/log", headers=admin_headers).json()
    assert body["lines"] == ["[hh2-media] Container entfernen\n"]


def test_log_missing(client, admin_headers, trigger: Path) -> None:
    body = client.get("/api/system/local-media/log", headers=admin_headers).json()
    assert body == {"exists": False, "lines": []}
