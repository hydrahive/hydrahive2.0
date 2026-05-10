"""Tests für POST /api/tailscale/install (Paket 1: Install via UI).

Mockt sowohl install_tailscale (subprocess) als auch get_status, weil der
Endpoint beide aufruft. So bleibt der Test unabhängig von einem echten
tailscale-Binary.
"""
from __future__ import annotations

from unittest.mock import patch


def test_install_requires_auth(client):
    """POST /api/tailscale/install ohne Token → 401."""
    r = client.post("/api/tailscale/install")
    assert r.status_code == 401


def test_install_requires_admin(client, auth_headers):
    """POST /api/tailscale/install als non-admin User → 403."""
    r = client.post("/api/tailscale/install", headers=auth_headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "admin_only"


def test_install_success_returns_status(client, admin_headers):
    """Bei rc=0 wird ok=true + frischer Status mitgeliefert."""
    async def fake_install():
        return {"ok": True, "rc": 0, "output": "[tailscale-install] Fertig."}
    async def fake_status():
        return {"installed": True, "connected": False, "backend_state": "NeedsLogin"}

    with patch("hydrahive.api.routes.tailscale.install_tailscale", fake_install), \
         patch("hydrahive.api.routes.tailscale.get_status", fake_status):
        r = client.post("/api/tailscale/install", headers=admin_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["rc"] == 0
    assert body["status"]["installed"] is True


def test_install_failure_returns_output(client, admin_headers):
    """Bei rc != 0 wird ok=false + Output durchgereicht (nicht 500)."""
    async def fake_install():
        return {"ok": False, "rc": 5, "output": "sudo: a password is required"}
    async def fake_status():
        return {"installed": False, "connected": False}

    with patch("hydrahive.api.routes.tailscale.install_tailscale", fake_install), \
         patch("hydrahive.api.routes.tailscale.get_status", fake_status):
        r = client.post("/api/tailscale/install", headers=admin_headers)

    assert r.status_code == 200  # bewusst 200 — Frontend zeigt Output an
    body = r.json()
    assert body["ok"] is False
    assert body["rc"] == 5
    assert "password" in body["output"]
    assert body["status"]["installed"] is False


def test_install_module_calls_correct_script(monkeypatch):
    """install_tailscale ruft sudo bash <base_dir>/installer/modules/80-tailscale.sh."""
    import asyncio
    from hydrahive.tailscale import install as install_mod

    captured = {}

    class FakeProc:
        returncode = 0
        async def communicate(self):
            return (b"ok\n", b"")
        def kill(self):  # pragma: no cover
            pass
        async def wait(self):  # pragma: no cover
            return 0

    async def fake_exec(*args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs.get("env")
        return FakeProc()

    # Skript-Existenz vortäuschen, sonst Early-Return
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    result = asyncio.run(install_mod.install_tailscale())

    assert result["ok"] is True
    assert captured["args"][0] == "sudo"
    assert captured["args"][1] == "-n"
    assert captured["args"][2] == "bash"
    assert captured["args"][3].endswith("/installer/modules/80-tailscale.sh")
    assert captured["env"]["HH_INSTALL_TAILSCALE"] == "yes"
