"""Alte Install-Wege laufen über den gemeinsamen Runner (Spec installer-core-first §3, „angleichen“).

Voice (POST /api/system/install-voice), Samba (POST /api/system/samba/setup) und Tailscale (POST /api/tailscale/install)
bleiben eine Version lang erreichbar, schreiben aber nur noch „install <modul>“ in .addon_request. Tailscale ruft
nicht mehr `sudo -n bash` aus dem Backend.
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


def test_voice_writes_addon_request(client, admin_headers, trigger: Path) -> None:
    r = client.post("/api/system/install-voice", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {"started": True}
    assert trigger.read_text() == "install voice\n"


def test_voice_busy_is_409(client, admin_headers, trigger: Path) -> None:
    trigger.write_text("install vms\n")
    r = client.post("/api/system/install-voice", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "addon_busy"


def test_voice_still_admin_only(client, auth_headers, trigger: Path) -> None:
    assert client.post("/api/system/install-voice", headers=auth_headers).status_code == 403
    assert not trigger.exists()


def test_samba_writes_addon_request_and_keeps_password_file(client, admin_headers, trigger: Path,
                                                            tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from hydrahive.settings import settings
    pwd = tmp_path / "samba.password"
    monkeypatch.setitem(settings.__dict__, "samba_password_file", pwd)
    r = client.post("/api/system/samba/setup", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {"started": True}
    assert trigger.read_text() == "install samba\n"
    assert pwd.exists() and oct(pwd.stat().st_mode & 0o777) == "0o600"


def test_samba_busy_is_409(client, admin_headers, trigger: Path) -> None:
    trigger.write_text("install voice\n")
    assert client.post("/api/system/samba/setup", headers=admin_headers).status_code == 409


def test_tailscale_writes_addon_request_without_sudo(client, admin_headers, trigger: Path) -> None:
    async def fake_status():
        return {"installed": False, "connected": False}

    async def no_exec(*a, **k):  # pragma: no cover - darf nicht passieren
        raise AssertionError("kein Subprozess aus dem Backend mehr")

    with patch("hydrahive.api.routes.tailscale.get_status", fake_status), \
         patch("asyncio.create_subprocess_exec", no_exec):
        r = client.post("/api/tailscale/install", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["started"] is True
    assert body["status"]["installed"] is False
    assert trigger.read_text() == "install tailscale\n"


def test_tailscale_busy_reports_not_ok(client, admin_headers, trigger: Path) -> None:
    async def fake_status():
        return {"installed": False, "connected": False}
    trigger.write_text("install vms\n")
    with patch("hydrahive.api.routes.tailscale.get_status", fake_status):
        r = client.post("/api/tailscale/install", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "addon_busy"


def test_old_sudo_installer_module_is_gone() -> None:
    assert not (Path(__file__).resolve().parents[1] / "src" / "hydrahive" / "tailscale" / "install.py").exists()


@pytest.mark.parametrize("addon", ["postgres", "local_media", "samba\ninstall vms", "../x", ""])
def test_shared_helper_enforces_the_list_itself(tmp_path: Path, addon: str) -> None:
    """request_install ist die einzige Stelle, die .addon_request schreibt – sie muss die Liste selbst durchsetzen,
    nicht nur die Route davor (Mutanten-Lücke 11.10.2026)."""
    from fastapi import HTTPException

    from hydrahive.api.routes._addon_request import request_install
    trigger = tmp_path / ".addon_request"
    with pytest.raises(HTTPException) as exc:
        request_install(addon, trigger)
    assert exc.value.status_code == 400
    assert not trigger.exists()
