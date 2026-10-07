"""Verwaiste Bridge von früher beim Start ablösen (Task 06d38ae9).

Bestandsinstallationen haben noch eine Waise aus der Zeit vor der Lebensader (Prod: seit 04.10.).
Sie hält Port 8767; jede neue Bridge stürbe mit EADDRINUSE. Abgelöst wird NUR ein Prozess, der
sicher unsere Bridge ist: `node index.js`, Arbeitsordner = Bridge-Verzeichnis, gleicher Nutzer.
Alles andere auf dem Port bleibt unangetastet → Bridge startet nicht, klare Log-Meldung.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from hydrahive.communication.whatsapp import _orphan
from hydrahive.communication.whatsapp.process import BRIDGE_DIR


class _P:
    def __init__(self, pid, cmdline, cwd, uid):
        self.pid, self.cmdline, self.cwd, self.uid = pid, cmdline, cwd, uid


def test_is_our_bridge_requires_all_three_marks():
    me = os.getuid()
    assert _orphan.is_our_bridge(_P(1, ["node", "index.js"], BRIDGE_DIR, me))
    assert _orphan.is_our_bridge(_P(1, ["/usr/bin/node", "index.js"], BRIDGE_DIR, me))
    assert not _orphan.is_our_bridge(_P(1, ["node", "index.js"], Path("/tmp/anders"), me))     # fremder Ordner
    assert not _orphan.is_our_bridge(_P(1, ["node", "server.js"], BRIDGE_DIR, me))             # anderes Skript
    assert not _orphan.is_our_bridge(_P(1, ["python3", "index.js"], BRIDGE_DIR, me))           # kein node
    assert not _orphan.is_our_bridge(_P(1, ["node", "index.js"], BRIDGE_DIR, me + 1))          # anderer Nutzer
    assert not _orphan.is_our_bridge(_P(1, [], None, me))                                      # unlesbar


def test_release_port_only_terminates_our_bridge(monkeypatch):
    killed = []
    procs = {11: _P(11, ["node", "index.js"], BRIDGE_DIR, os.getuid()),
             12: _P(12, ["nginx"], Path("/"), os.getuid())}
    monkeypatch.setattr(_orphan, "listeners", lambda port: [11, 12])
    monkeypatch.setattr(_orphan, "describe", lambda pid: procs.get(pid))
    monkeypatch.setattr(_orphan, "_terminate", lambda pid: killed.append(pid) or True)
    assert _orphan.release_port(8767) == {"terminated": [11], "foreign": [12]}
    assert killed == [11]


def test_release_port_free_port_does_nothing(monkeypatch):
    monkeypatch.setattr(_orphan, "listeners", lambda port: [])
    monkeypatch.setattr(_orphan, "_terminate", lambda pid: pytest.fail("darf nichts beenden"))
    assert _orphan.release_port(8767) == {"terminated": [], "foreign": []}


def test_start_refuses_when_foreign_process_holds_port(monkeypatch, tmp_path, caplog):
    from hydrahive.communication.whatsapp.process import BridgeProcess
    monkeypatch.setattr(BridgeProcess, "_has_node", staticmethod(lambda: True))
    monkeypatch.setattr(BridgeProcess, "_modules_installed", staticmethod(lambda: True))
    monkeypatch.setattr(_orphan, "release_port", lambda port: {"terminated": [], "foreign": [4711]})
    started = []

    async def fake_exec(*a, **k):
        started.append(a)
        raise AssertionError("darf nicht starten")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    b = BridgeProcess(port=8767, data_dir=tmp_path, backend_url="http://x", secret="s")
    with caplog.at_level("ERROR"):
        assert asyncio.run(b.start()) is False
    assert not started and "8767" in caplog.text and "4711" in caplog.text


@pytest.mark.skipif(sys.platform != "linux" or shutil.which("node") is None, reason="Linux + node nötig")
def test_real_orphan_is_found_and_terminated(tmp_path):
    """Echter Prozess: node index.js im (kopierten) Bridge-Ordner, lauscht auf einem freien Port."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    d = tmp_path / "bridge"
    d.mkdir()
    (d / "index.js").write_text(
        f'require("http").createServer((q, r) => r.end("ok")).listen({port}, "127.0.0.1");', encoding="utf-8")
    p = subprocess.Popen(["node", "index.js"], cwd=d, stdin=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if _orphan.listeners(port):
                break
            asyncio.run(asyncio.sleep(0.1))
        assert _orphan.listeners(port) == [p.pid]
        info = _orphan.describe(p.pid)
        assert info.cwd == d and info.cmdline[-1] == "index.js" and info.uid == os.getuid()
        assert _orphan._terminate(p.pid) is True
        assert p.wait(timeout=5) == -signal.SIGTERM
        assert _orphan.listeners(port) == []
    finally:
        if p.poll() is None:
            p.kill()
