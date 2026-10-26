"""Tailscale auf dem Mac (Plan docs/plans/mac-tailscale.md): Zusatz-Modul, CLI-Suche, Anmeldung per Link."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from hydrahive.system import addons_status as st
from hydrahive.tailscale import _bin
from hydrahive.tailscale import control

ALL = ["containers", "vms", "samba", "whatsapp", "voice", "tailscale"]


# --- Zusatz-Modul ------------------------------------------------------------------------------------------

def test_tailscale_installable_on_mac(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "PROBES", {a: (lambda: False) for a in ALL})
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    monkeypatch.setattr(st, "is_mac", lambda: True)
    items = {i["id"]: i for i in st.list_addons(tmp_path / "install.conf")}
    assert items["tailscale"]["hint"] is None
    assert items["containers"]["hint"] is None
    assert all(items[a]["hint"] == "mac" for a in ("vms", "whatsapp"))
    assert items["samba"]["hint"] is None                       # macOS-Dateifreigabe (docs/plans/mac-file-sharing.md)


# --- CLI-Suche --------------------------------------------------------------------------------------------------

def _exe(p: Path) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/sh\n")
    p.chmod(0o755)
    return str(p)


def test_own_mac_build_found_without_path(monkeypatch, tmp_path):
    own = _exe(tmp_path / "ts" / "bin" / "tailscale")
    monkeypatch.setattr(_bin.shutil, "which", lambda n: None)
    monkeypatch.setattr(_bin, "MAC_OWN_CLI", own)
    monkeypatch.setattr(_bin, "MACOS_APP_CLI", str(tmp_path / "fehlt"))
    assert _bin.find_tailscale() == own


def test_ohne_app_path_dann_eigener_build(monkeypatch, tmp_path):
    own = _exe(tmp_path / "own" / "tailscale")
    monkeypatch.setattr(_bin, "MAC_OWN_CLI", own)
    monkeypatch.setattr(_bin, "MACOS_APP_CLI", str(tmp_path / "keine-app"))
    monkeypatch.setattr(_bin.shutil, "which", lambda n: "/im/path/tailscale")
    assert _bin.find_tailscale() == "/im/path/tailscale"
    monkeypatch.setattr(_bin.shutil, "which", lambda n: None)
    assert _bin.find_tailscale() == own
    os.remove(own)
    assert _bin.find_tailscale() is None


def test_app_hat_vorrang_vor_path_und_eigenem_build(monkeypatch, tmp_path):
    """Befund Berkan 26.10.: Der Backend-PATH enthält den eigenen bin-Ordner – gefragt wurde die tote eigene CLI,
    obwohl die Tailscale-App lief und angemeldet war. Ist die App da, gilt sie (beide vertragen sich nicht)."""
    own = _exe(tmp_path / "own" / "bin" / "tailscale")
    app = _exe(tmp_path / "app" / "Tailscale")
    monkeypatch.setattr(_bin, "MAC_OWN_CLI", own)
    monkeypatch.setattr(_bin, "MACOS_APP_CLI", app)
    monkeypatch.setattr(_bin.shutil, "which", lambda n: own)          # PATH zeigt auf den eigenen Build
    assert _bin.find_tailscale() == app
    monkeypatch.setattr(_bin.shutil, "which", lambda n: "/opt/homebrew/bin/tailscale")
    assert _bin.find_tailscale() == app


def test_app_ohne_ausfuehrrecht_zaehlt_nicht(monkeypatch, tmp_path):
    app = tmp_path / "app" / "Tailscale"
    app.parent.mkdir(parents=True)
    app.write_text("x")
    app.chmod(0o644)
    monkeypatch.setattr(_bin, "MACOS_APP_CLI", str(app))
    monkeypatch.setattr(_bin.shutil, "which", lambda n: "/im/path/tailscale")
    assert _bin.find_tailscale() == "/im/path/tailscale"


# --- Anmeldung per Link ---------------------------------------------------------------------------------------

class _FakeProc:
    """`tailscale up --json`: erst ein JSON-Block mit AuthURL, dann (nach der Anmeldung) einer mit Running."""

    def __init__(self, lines: list[bytes]):
        self.lines = lines
        self.stdout: asyncio.StreamReader | None = None
        self.returncode = None
        self.killed = False

    def start(self) -> "_FakeProc":
        self.stdout = asyncio.StreamReader()                    # braucht eine laufende Schleife
        for ln in self.lines:
            self.stdout.feed_data(ln)
        return self

    def kill(self):
        self.killed = True

    async def wait(self):
        return 0


def test_login_returns_auth_url(monkeypatch):
    proc = _FakeProc([b'{\n', b'\t"AuthURL": "https://login.tailscale.com/a/abc123",\n', b'\t"QR": "data:x",\n',
                      b'\t"BackendState": "NeedsLogin"\n', b'}\n'])
    seen = []

    async def fake_exec(*args, **kw):
        seen.append(args)
        return proc.start()

    monkeypatch.setattr(control.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(control, "_tailscale_bin", lambda: "/x/tailscale")
    url = asyncio.run(control.login(timeout=2))
    assert url == "https://login.tailscale.com/a/abc123"
    assert seen[0][:3] == ("/x/tailscale", "up", "--json")
    assert "--authkey" not in " ".join(seen[0])
    assert not proc.killed                       # läuft weiter, bis die Anmeldung im Browser fertig ist


def test_login_already_running(monkeypatch):
    proc = _FakeProc([b'{\n', b'\t"BackendState": "Running"\n', b'}\n'])

    async def fake_exec(*args, **kw):
        return proc.start()

    monkeypatch.setattr(control.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(control, "_tailscale_bin", lambda: "/x/tailscale")
    assert asyncio.run(control.login(timeout=2)) is None


def test_login_timeout_kills_process(monkeypatch):
    proc = _FakeProc([b"{\n"])                    # nie fertig

    async def fake_exec(*args, **kw):
        return proc.start()

    monkeypatch.setattr(control.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(control, "_tailscale_bin", lambda: "/x/tailscale")
    with pytest.raises(RuntimeError):
        asyncio.run(control.login(timeout=0.3))
    assert proc.killed


def test_login_only_tailscale_urls(monkeypatch):
    proc = _FakeProc([b'{"AuthURL": "https://evil.example/a/x", "BackendState": "NeedsLogin"}\n'])

    async def fake_exec(*args, **kw):
        return proc.start()

    monkeypatch.setattr(control.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(control, "_tailscale_bin", lambda: "/x/tailscale")
    with pytest.raises(RuntimeError):
        asyncio.run(control.login(timeout=2))


def test_login_route_admin_only(client, auth_headers, admin_headers, monkeypatch):
    from hydrahive.api.routes import tailscale as route

    async def fake_login(timeout: float = 20):
        return "https://login.tailscale.com/a/abc123"

    monkeypatch.setattr(route, "login", fake_login)
    assert client.post("/api/tailscale/login").status_code == 401
    assert client.post("/api/tailscale/login", headers=auth_headers).status_code == 403
    r = client.post("/api/tailscale/login", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {"auth_url": "https://login.tailscale.com/a/abc123"}


# --- Status vor der Anmeldung (Befund 21.10.2026, Test-Mac) ---------------------------------------------------

def test_status_needs_login_with_null_ips(monkeypatch):
    """Frisch installiert, noch nicht angemeldet: `TailscaleIPs: null`, `Peer` fehlt. Vorher stürzte get_status mit
    „'NoneType' object is not iterable“ ab → Karte zeigte keinen Anmelde-Link (auch unter Linux)."""
    from hydrahive.tailscale import status

    out = ('{"Version":"1.104.2-hydrahive","BackendState":"NeedsLogin",'
           '"AuthURL":"https://login.tailscale.com/a/abc","TailscaleIPs":null,'
           '"Self":{"HostName":"","DNSName":"","TailscaleIPs":null},"Peer":null,"MagicDNSSuffix":""}')

    async def fake_run(*args, timeout=5):
        return 0, out, ""

    monkeypatch.setattr(status, "_run", fake_run)
    s = asyncio.run(status.get_status())
    assert s["installed"] is True and s["connected"] is False
    assert s["backend_state"] == "NeedsLogin"
    assert s["auth_url"] == "https://login.tailscale.com/a/abc"
    assert s["ip"] is None and s["peers"] == []
    assert "error" not in s


# --- Fehler bei der Anmeldung verständlich (Befund Berkan: internal_error) --------------------------------------

def test_login_meldet_tailscale_fehlertext(monkeypatch):
    """tailscale up endet sofort mit Fehler (Dienst nicht erreichbar) → der Grund steht im Fehlertext."""
    class P(_FakeProc):
        def __init__(self):
            super().__init__([])
            self.stderr = None

        def start(self):
            super().start()
            self.stderr = asyncio.StreamReader()
            self.stderr.feed_data(b"failed to connect to local Tailscale service; is Tailscale running?\n")
            self.stderr.feed_eof()
            assert self.stdout is not None
            self.stdout.feed_eof()
            return self

    async def fake_exec(*a, **kw):
        assert kw.get("stderr") == asyncio.subprocess.PIPE
        return P().start()

    monkeypatch.setattr(control.asyncio, "create_subprocess_exec", fake_exec)
    with pytest.raises(RuntimeError) as e:
        asyncio.run(control.login(timeout=2))
    assert "failed to connect to local Tailscale service" in str(e.value)


def test_login_programm_fehlt_kein_internal_error(monkeypatch):
    async def fake_exec(*a, **kw):
        raise FileNotFoundError(2, "No such file or directory")
    monkeypatch.setattr(control.asyncio, "create_subprocess_exec", fake_exec)
    with pytest.raises(RuntimeError) as e:
        asyncio.run(control.login(timeout=2))
    assert "Tailscale" in str(e.value)


def test_login_route_startfehler_502(client, admin_headers, monkeypatch):
    from hydrahive.api.routes import tailscale as route

    async def boom():
        raise RuntimeError("Tailscale nicht erreichbar: failed to connect")
    monkeypatch.setattr(route, "login", boom)
    r = client.post("/api/tailscale/login", headers=admin_headers)
    assert r.status_code == 502
    assert "failed to connect" in r.json()["detail"]
