"""Verwaiste WhatsApp-Bridge von früher beim Start ablösen (Task 06d38ae9).

Vor der stdin-Lebensader (bridge/lib/lifeline.js) überlebte die Bridge ein hartes Ende des Backends
und hielt ihren Port – jede neue Bridge starb mit EADDRINUSE. Diese Waisen laufen auf Bestands-
installationen noch. Beim Start wird der Port geprüft:
- Lauscht dort **unsere** Bridge (``node index.js``, Arbeitsordner = Bridge-Verzeichnis, gleicher
  Nutzer), wird sie mit SIGTERM beendet (sie schließt sauber).
- Alles andere bleibt unangetastet; die Bridge startet dann nicht (klare Log-Meldung).
Linux liest /proc, macOS fragt ``lsof``. Fehlt beides, wird nichts beendet.
"""
from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

BRIDGE_DIR = Path(__file__).resolve().parent / "bridge"
_WAIT_S = 5.0


@dataclass
class ProcInfo:
    pid: int
    cmdline: list[str]
    cwd: Path | None
    uid: int | None


def _lsof(args: list[str]) -> str:
    if not shutil.which("lsof"):
        return ""
    try:
        return subprocess.run(["lsof", *args], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def listeners(port: int) -> list[int]:
    """PIDs, die auf 127.0.0.1:<port> (TCP) lauschen – nur eigene Prozesse sind sichtbar, das genügt."""
    out = _lsof(["-nP", "-t", f"-iTCP@127.0.0.1:{port}", "-sTCP:LISTEN"])
    return sorted({int(x) for x in out.split() if x.isdigit()})


def describe(pid: int) -> ProcInfo | None:
    proc = Path("/proc") / str(pid)
    if sys.platform.startswith("linux") and proc.is_dir():
        try:
            cmd = [c for c in (proc / "cmdline").read_bytes().decode(errors="replace").split("\0") if c]
            return ProcInfo(pid, cmd, Path(os.readlink(proc / "cwd")), proc.stat().st_uid)
        except OSError:
            return None
    out = _lsof(["-a", "-p", str(pid), "-d", "cwd", "-Fnu"])          # macOS
    cwd = next((Path(line[1:]) for line in out.splitlines() if line.startswith("n")), None)
    uid = next((int(line[1:]) for line in out.splitlines() if line.startswith("u") and line[1:].isdigit()), None)
    try:
        cmd = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True,
                             timeout=5).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        cmd = []
    return ProcInfo(pid, cmd, cwd, uid) if cmd else None


def is_our_bridge(p: ProcInfo | None) -> bool:
    if p is None or not p.cmdline or p.cwd is None:
        return False
    return (Path(p.cmdline[0]).name == "node" and p.cmdline[1:] == ["index.js"]
            and p.cwd.resolve() == BRIDGE_DIR.resolve() and p.uid == os.getuid())


def _gone(pid: int) -> bool:
    """Prozess beendet? Ein Zombie (beendet, Eltern hat noch nicht abgeholt) zählt als beendet."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    stat = Path("/proc") / str(pid) / "stat"
    try:
        return stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    except (OSError, IndexError):
        return False


def _terminate(pid: int) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    deadline = time.monotonic() + _WAIT_S
    while time.monotonic() < deadline:
        if _gone(pid):
            return True
        time.sleep(0.1)
    return False


def release_port(port: int) -> dict[str, list[int]]:
    """Unsere verwaiste Bridge auf ``port`` beenden. Ergebnis: beendete und fremde PIDs."""
    out: dict[str, list[int]] = {"terminated": [], "foreign": []}
    for pid in listeners(port):
        if pid == os.getpid():
            continue
        if is_our_bridge(describe(pid)) and _terminate(pid):
            logger.warning("Verwaiste WhatsApp-Bridge (PID %s) auf Port %s beendet", pid, port)
            out["terminated"].append(pid)
        else:
            out["foreign"].append(pid)
    return out
