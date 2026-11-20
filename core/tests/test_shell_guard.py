"""Harte Shell-Sperre für Projekt-Agenten und Spezialisten (tools/_shell_guard.py).

Vorfall 20.11.2026: Ein Spezialist ging per ssh auf Tills Workstation, nutzte sudo
und las Geheimnisse. Die Befehle unten sind wörtlich aus dem Verlauf (Session 01a1f5e5).
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.tools import _shell_guard as g
from hydrahive.tools import shell
from hydrahive.tools.base import ToolContext

VORFALL = [
    'ssh 192.168.178.197 "echo OK; whoami; hostname" 2>&1 | head -20',
    'ssh 192.168.178.197 "sudo -n true 2>&1 && echo HAVE_SUDO || echo NO_SUDO" 2>&1',
    'cat ~/.ssh/config 2>/dev/null',
    'ls /var/lib/hydrahive2/.ssh/config 2>/dev/null\ncat /var/lib/hydrahive2/.ssh/config 2>/dev/null',
    "sudo cat /proc/$(pgrep -f 'uvicorn hydrahive.api.main' | head -1)/environ | tr '\\0' '\\n'",
    'sudo -u hydrahive cat /etc/hydrahive2/pg_mirror.dsn',
    'DSN=$(cat /etc/hydrahive2/pg_mirror.dsn); psql "$DSN" -c "\\dt"',
    'cat /etc/hydrahive2/users.json | python3 -c "import json,sys"',
]

GESPERRT = [
    "scp datei.txt till@192.168.178.197:/tmp/",
    "sshpass -p geheim ssh root@10.0.0.1 ls",
    "rsync -av ./ till@wks197:/srv/backup/",
    "timeout 5 ssh -o BatchMode=yes host true",
    "FOO=1 env ssh host",
    "cd /tmp && sudo bash",
    "echo x | sudo tee /etc/hosts",
    "su - root",
    "incus exec hydrahive2-stt -- bash",
    "docker run -v /:/host alpine cat /host/etc/shadow",
    "bash -c 'ssh host uptime'",
    "echo $(ssh host cat /etc/hostname)",
    "nc 192.168.178.197 22",
    "cat /proc/self/environ",
    "grep -r token /var/lib/hydrahive2/credentials/",
    "cat /home/till/.netrc",
    "openssl x509 -in /srv/certs/server.pem",
]

ERLAUBT = [
    "git push origin feat/x",
    "git clone git@github.com:hydrahive/hydrahive2-modules.git",
    "PYTHONPATH=src pytest -q tests",
    "rsync -a ./build/ /tmp/out/",
    "grep -rn 'ssh' src/hydrahive/tools/shell.py",
    "docker ps",
    "ls -la && cat README.md | head",
    "python3 -c 'print(1)'",
    "curl -s http://127.0.0.1:8001/api/health",
]


@pytest.mark.parametrize("cmd", VORFALL)
def test_vorfall_befehle_gesperrt(cmd):
    assert g.check_text(cmd), cmd


@pytest.mark.parametrize("cmd", GESPERRT)
def test_weitere_wege_gesperrt(cmd):
    assert g.check_text(cmd), cmd


@pytest.mark.parametrize("cmd", ERLAUBT)
def test_normale_arbeit_erlaubt(cmd):
    assert g.check_text(cmd) is None, f"{cmd} → {g.check_text(cmd)}"


@pytest.mark.parametrize("kind,blocked", [("specialist", True), ("project", True), ("master", False), (None, True)])
def test_nur_projekt_und_spezialist_gesperrt(monkeypatch, kind, blocked):
    monkeypatch.setattr(g, "agent_type", lambda _aid: kind)
    assert bool(g.blocked_reason("ssh host ls", "a1")) is blocked


def test_shell_exec_fuehrt_gesperrten_befehl_nicht_aus(monkeypatch, tmp_path):
    """Ende-zu-Ende über das Werkzeug: Ablehnung OHNE Ausführung, mit Blocker-Hinweis."""
    monkeypatch.setattr(g, "agent_type", lambda _aid: "specialist")
    ran = []

    class FakeLauncher:
        async def run(self, cmd, **kw):
            ran.append(cmd)

    monkeypatch.setattr(shell._launcher_container, "launcher_for", lambda ctx: FakeLauncher())
    ctx = ToolContext(session_id="s", agent_id="spez", user_id="till", workspace=tmp_path)
    res = asyncio.run(shell._execute({"cmd": VORFALL[0]}, ctx))
    assert res.success is False and ran == []
    assert "fremde Rechner" in res.error and "Blocker" in res.error
    assert res.metadata.get("blocked") == "guard"


def test_werkzeugbeschreibung_bewirbt_kein_ssh_mehr():
    assert "ssh user@host" not in shell._DESCRIPTION and "sshpass -p" not in shell._DESCRIPTION
