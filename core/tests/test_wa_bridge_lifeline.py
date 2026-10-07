"""WhatsApp-Bridge beendet sich, wenn ihr Backend weg ist (Task 06d38ae9).

Wird das Backend hart beendet (SIGKILL nach Stop-Timeout), überlebte die Node-Bridge
(KillMode=process) und blockierte den Port – jede neue Bridge starb mit EADDRINUSE.
Lebensader: Python hält stdin offen; EOF auf stdin → Bridge schließt sich.
Echter Node-Prozess, ohne Abhängigkeiten (lib/lifeline.js braucht kein baileys).
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest

BRIDGE = Path(__file__).resolve().parents[1] / "src" / "hydrahive" / "communication" / "whatsapp" / "bridge"
LIFELINE = BRIDGE / "lib" / "lifeline.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node fehlt")

_SCRIPT = """
import { watchParent } from %s;
console.log("bereit");
watchParent(() => { console.log("ende"); process.exit(0); });
setInterval(() => {}, 1000);
"""


def _start(tmp_path: Path) -> subprocess.Popen:
    script = tmp_path / "probe.mjs"
    script.write_text(_SCRIPT % repr(LIFELINE.as_uri()), encoding="utf-8")
    p = subprocess.Popen(["node", str(script)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "bereit"
    return p


def test_bridge_ends_when_stdin_closes(tmp_path: Path) -> None:
    p = _start(tmp_path)
    try:
        time.sleep(0.3)
        assert p.poll() is None                    # läuft, solange das Backend lebt
        p.stdin.close()                            # Backend weg (auch SIGKILL schließt die Pipe)
        assert p.wait(timeout=5) == 0
        assert "ende" in p.stdout.read()
    finally:
        if p.poll() is None:
            p.kill()


def test_bridge_keeps_running_while_stdin_open(tmp_path: Path) -> None:
    p = _start(tmp_path)
    try:
        time.sleep(1.5)
        assert p.poll() is None
    finally:
        p.kill()
        p.wait()


def test_index_uses_lifeline_and_python_passes_pipe() -> None:
    index = (BRIDGE / "index.js").read_text(encoding="utf-8")
    assert 'from "./lib/lifeline.js"' in index and "watchParent(" in index
    process_py = (BRIDGE.parent / "process.py").read_text(encoding="utf-8")
    assert "stdin=asyncio.subprocess.PIPE" in process_py


@pytest.mark.skipif(not (BRIDGE / "node_modules" / "@whiskeysockets" / "baileys").exists(),
                    reason="Bridge-Abhängigkeiten fehlen (npm install)")
def test_real_bridge_frees_port_when_stdin_closes(tmp_path: Path) -> None:
    import socket
    import urllib.request
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HH_WA_BRIDGE_PORT": str(port), "HH_WA_BRIDGE_SECRET": "x",
           "HH_WA_DATA_DIR": str(tmp_path), "HH_WA_BACKEND_URL": "http://127.0.0.1:1"}
    p = subprocess.Popen(["node", "index.js"], cwd=BRIDGE, env=env, stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                assert urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1).status == 200
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("Bridge startet nicht")
        p.stdin.close()
        assert p.wait(timeout=5) == 0
    finally:
        if p.poll() is None:
            p.kill()
