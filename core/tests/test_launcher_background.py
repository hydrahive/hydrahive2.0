"""shell_exec mit Hintergrundprozessen (Task 8c57e26f).

Der Server läuft mit uvloop. uvloop gibt Kindprozessen Duplikate seiner
Ausgabe-Sockets mit. Ein Hintergrundprozess (`cmd &`) hielt sie offen, der
Launcher wartete per communicate() auf EOF, also bis der Hintergrundprozess
endete, und stürzte beim Timeout mit ProcessLookupError ab.

Vereinbartes Verhalten (Till 30.09.2026, Variante A):
- Das Tool kehrt zurück, sobald bash fertig ist.
- Hintergrundprozesse laufen danach weiter.
- Bei Timeout wird die ganze Prozessgruppe beendet, mit setsid Gestartetes überlebt.
Jeder Test läuft unter uvloop (wie der Server) und unter asyncio.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import signal
import time
from pathlib import Path

import pytest

from hydrahive.tools._launcher import DevLauncher

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash nicht verfügbar")

LOOPS = ["asyncio", "uvloop"]


def _run(loop: str, cmd: str, cwd: Path, timeout: int = 20):
    coro = DevLauncher().run(cmd, cwd=cwd, timeout=timeout)
    if loop == "uvloop":
        uvloop = pytest.importorskip("uvloop")
        return uvloop.run(coro)
    return asyncio.run(coro)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # Zombie zählt als tot
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except OSError:
        return False


def _gone_within(pid: int, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return not _alive(pid)


@pytest.fixture
def pids():
    started: list[int] = []
    yield started
    for pid in started:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _pid(path: Path, pids: list[int]) -> int:
    pid = int(path.read_text().strip())
    pids.append(pid)
    return pid


@pytest.mark.parametrize("loop", LOOPS)
def test_kehrt_zurueck_sobald_bash_fertig_ist(loop, tmp_path, pids):
    t0 = time.monotonic()
    res = _run(loop, "sleep 30 > /dev/null 2>&1 < /dev/null & echo $! > bg.pid; echo fertig", tmp_path)
    took = time.monotonic() - t0
    pid = _pid(tmp_path / "bg.pid", pids)
    assert took < 3, f"wartete {took:.1f}s auf den Hintergrundprozess"
    assert not res.timed_out
    assert res.exit_code == 0
    assert res.stdout.strip() == "fertig"
    assert _alive(pid), "Variante A: Hintergrundprozess muss nach normalem Ende weiterlaufen"


@pytest.mark.parametrize("loop", LOOPS)
def test_timeout_stuerzt_nicht_ab_und_beendet_die_gruppe(loop, tmp_path, pids):
    t0 = time.monotonic()
    res = _run(loop, "sleep 30 > /dev/null 2>&1 < /dev/null & echo $! > bg.pid; sleep 30", tmp_path, timeout=1)
    took = time.monotonic() - t0
    pid = _pid(tmp_path / "bg.pid", pids)
    assert res.timed_out
    assert res.exit_code == -1
    assert took < 5
    assert _gone_within(pid, 3), "Hintergrundprozess der Gruppe muss beim Timeout mit beendet werden"


@pytest.mark.parametrize("loop", LOOPS)
def test_timeout_laesst_setsid_prozess_leben(loop, tmp_path, pids):
    res = _run(loop, "setsid sleep 30 > /dev/null 2>&1 < /dev/null & echo $! > bg.pid; sleep 30", tmp_path, timeout=1)
    pid = _pid(tmp_path / "bg.pid", pids)
    assert res.timed_out
    time.sleep(0.3)
    assert _alive(pid), "mit setsid Gestartetes soll den Timeout überleben"


@pytest.mark.parametrize("loop", LOOPS)
def test_spaete_ausgabe_eines_hintergrundprozesses_blockiert_nicht(loop, tmp_path, pids):
    t0 = time.monotonic()
    res = _run(loop, "(sleep 5; echo spaet) & echo $! > bg.pid; echo frueh", tmp_path)
    took = time.monotonic() - t0
    _pid(tmp_path / "bg.pid", pids)
    assert took < 3, f"wartete {took:.1f}s"
    assert "frueh" in res.stdout
    assert "spaet" not in res.stdout


@pytest.mark.parametrize("loop", LOOPS)
def test_grosse_ausgabe_kommt_vollstaendig_an(loop, tmp_path):
    res = _run(loop, "head -c 3000000 /dev/zero | tr '\\0' a; echo; echo fehler >&2", tmp_path)
    assert res.exit_code == 0
    assert res.stdout.count("a") == 3_000_000
    assert res.stderr.strip() == "fehler"


@pytest.mark.parametrize("loop", LOOPS)
def test_eigene_prozessgruppe(loop, tmp_path):
    res = _run(loop, "ps -o pgid= -p $$", tmp_path)
    assert int(res.stdout.strip()) != os.getpgrp(), "Befehl darf nicht in der Prozessgruppe des Servers laufen"


@pytest.mark.parametrize("loop", LOOPS)
def test_exit_code_und_stderr_bleiben(loop, tmp_path):
    res = _run(loop, "echo raus; echo kaputt >&2; exit 3", tmp_path)
    assert res.exit_code == 3
    assert res.stdout.strip() == "raus"
    assert res.stderr.strip() == "kaputt"
    assert not res.timed_out


@pytest.mark.parametrize("loop", LOOPS)
def test_timeout_beendet_auch_prozesse_die_sigterm_ignorieren(loop, tmp_path, pids):
    res = _run(loop, "(trap '' TERM; exec sleep 30) > /dev/null 2>&1 < /dev/null & echo $! > bg.pid; sleep 30",
               tmp_path, timeout=1)
    pid = _pid(tmp_path / "bg.pid", pids)
    assert res.timed_out
    assert _gone_within(pid, 3)


def test_kill_group_leere_gruppe_wirft_nicht():
    import subprocess

    from hydrahive.tools._launcher import _kill_group
    p = subprocess.Popen(["true"], start_new_session=True)
    p.wait()
    _kill_group(p.pid)  # Gruppe existiert nicht mehr: darf nicht werfen


@pytest.mark.parametrize("loop", LOOPS)
def test_stopp_beendet_den_befehl(loop, tmp_path, pids):
    """Lauf gestoppt (CancelledError) → Befehl und seine Kinder enden mit.
    Auf dem Test-Server gefunden (01.10.2026): Nach „Auftrag abbrechen“ lief
    `sleep 120` des Spezialisten verwaist weiter."""
    async def go():
        task = asyncio.ensure_future(DevLauncher().run(
            "sleep 30 > /dev/null 2>&1 < /dev/null & echo $! > bg.pid; sleep 30 & echo $! > fg.pid; wait",
            cwd=tmp_path, timeout=60))
        for _ in range(100):
            if (tmp_path / "fg.pid").exists() and (tmp_path / "fg.pid").read_text().strip():
                break
            await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    if loop == "uvloop":
        pytest.importorskip("uvloop").run(go())
    else:
        asyncio.run(go())
    for name in ("bg.pid", "fg.pid"):
        pid = _pid(tmp_path / name, pids)
        assert _gone_within(pid, 3), f"{name}: Prozess läuft nach dem Stopp weiter"
