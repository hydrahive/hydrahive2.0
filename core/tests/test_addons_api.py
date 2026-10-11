"""API der Zusatz-Module (Spec installer-core-first §3): nur Admin, Anfrage-Datei mit fester Zeile, 409/400, Log.

Ausgeführt wird als root von hydrahive2-addon.service über installer/addon-ctl.sh (test_addon_ctl.py).
"""
from __future__ import annotations

from pathlib import Path

import pytest

ITEM = {"installed": False, "enabled": False, "restarts_service": False, "requires": [], "hint": None}


# Routen-Modul erst in den Fixtures importieren (settings.data_dir ist cached, siehe test_local_media_api.py).
@pytest.fixture
def route():
    from hydrahive.api.routes import system_addons
    return system_addons


@pytest.fixture
def trigger(tmp_path: Path, route, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / ".addon_request"
    monkeypatch.setattr(route, "_trigger", lambda: path)
    return path


@pytest.fixture
def log_file(tmp_path: Path, route, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "hydrahive2-addon.log"
    monkeypatch.setattr(route, "_log_path", lambda: path)
    return path


@pytest.fixture
def installed(route, monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """Welche Module als installiert gelten – Test setzt die Menge."""
    have: set[str] = set()
    ids = ["containers", "vms", "samba", "whatsapp", "voice", "tailscale"]
    monkeypatch.setattr(route, "list_addons",
                        lambda conf=None: [{**ITEM, "id": a, "installed": a in have} for a in ids])
    return have


def test_requires_auth(client) -> None:
    assert client.get("/api/system/addons").status_code == 401
    assert client.post("/api/system/addons/samba/install").status_code == 401


def test_requires_admin(client, auth_headers, trigger: Path) -> None:
    assert client.get("/api/system/addons", headers=auth_headers).status_code == 403
    assert client.post("/api/system/addons/samba/install", headers=auth_headers).status_code == 403
    assert client.get("/api/system/addons/log", headers=auth_headers).status_code == 403
    assert not trigger.exists()


def test_list_reports_items_and_running(client, admin_headers, trigger: Path, installed) -> None:
    installed.add("samba")
    body = client.get("/api/system/addons", headers=admin_headers).json()
    assert body["running"] is None
    assert {i["id"]: i["installed"] for i in body["items"]}["samba"] is True
    trigger.write_text("install vms\n")
    assert client.get("/api/system/addons", headers=admin_headers).json()["running"] == "vms"


def test_install_writes_one_fixed_line(client, admin_headers, trigger: Path, installed) -> None:
    r = client.post("/api/system/addons/whatsapp/install", headers=admin_headers)
    assert r.status_code == 202
    assert r.json() == {"started": True}
    assert trigger.read_text() == "install whatsapp\n"


@pytest.mark.parametrize("addon", ["postgres", "local_media", "SAMBA", "samba;id", "x" * 40])
def test_unknown_addon_is_rejected(client, admin_headers, trigger: Path, installed, addon: str) -> None:
    r = client.post(f"/api/system/addons/{addon}/install", headers=admin_headers)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "addon_unknown"
    assert not trigger.exists()


def test_second_request_while_running_is_409(client, admin_headers, trigger: Path, installed) -> None:
    trigger.write_text("install vms\n")
    r = client.post("/api/system/addons/samba/install", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "addon_busy"
    assert trigger.read_text() == "install vms\n"


def test_already_installed_is_409(client, admin_headers, trigger: Path, installed) -> None:
    installed.add("samba")
    r = client.post("/api/system/addons/samba/install", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "addon_installed"
    assert not trigger.exists()


def test_log_tail_capped_and_colour_free(client, admin_headers, log_file: Path) -> None:
    log_file.write_text("\x1b[1;36m[x]\x1b[0m a\n" + "".join(f"zeile {i}\n" for i in range(3000)))
    body = client.get("/api/system/addons/log?tail=99999", headers=admin_headers).json()
    assert body["exists"] is True and len(body["lines"]) == 1000 and body["lines"][-1] == "zeile 2999\n"
    log_file.write_text("\x1b[1;36m[hh2-addon]\x1b[0m los\n")
    assert client.get("/api/system/addons/log", headers=admin_headers).json()["lines"] == ["[hh2-addon] los\n"]


def test_log_missing(client, admin_headers, log_file: Path) -> None:
    assert client.get("/api/system/addons/log", headers=admin_headers).json() == {"exists": False, "lines": []}
