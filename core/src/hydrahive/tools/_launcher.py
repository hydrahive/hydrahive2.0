from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Protocol

logger = logging.getLogger(__name__)

# Agenten-Shell läuft in bash, nicht im default /bin/sh (dash). LLMs generieren
# ständig Bashisms (`[[ ]]`, Prozesssubstitution, Arrays) — in dash failen die
# mit kryptischen Syntaxfehlern. Fallback auf den Shell-Default, falls bash fehlt
# (minimale Container), damit shell_exec nie ganz bricht.
_BASH = shutil.which("bash")


@dataclass
class LaunchResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class Launcher(Protocol):
    """Spawns a subprocess. Implementations decide on isolation level."""

    async def run(
        self,
        cmd: str,
        cwd: Path,
        timeout: int = 60,
        env: dict | None = None,
    ) -> LaunchResult: ...


def _read(f: IO[bytes]) -> str:
    f.seek(0)
    return f.read().decode("utf-8", errors="replace")


def _kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # Gruppe schon leer


class DevLauncher:
    """Spawns subprocesses as the service user inside `cwd`.

    This is the production launcher. Privilege-separation per Agent (systemd-run
    + dedicated users) is out of scope for the project's threat-model (home-lab,
    trusted agents with intentional full tool access).

    Hintergrundprozesse (`cmd &`, Task 8c57e26f):
    - Ausgabe geht in temporäre Dateien, nicht in Pipes. Der Server läuft mit
      uvloop, und uvloop gibt dem Kind Kopien seiner Ausgabe-Sockets als weitere
      Deskriptoren mit (auch mit close_fds). Ein Hintergrundprozess erbt sie trotz
      `> /dev/null` und `setsid`, communicate() wartete dann bis zu seinem Ende
      bzw. zum Timeout und stürzte dort mit ProcessLookupError ab.
    - Bekannte Grenze: Ein Hintergrundprozess OHNE Umleitung schreibt nach dem
      Ende von bash in die schon gelöschte Temp-Datei weiter, bis er endet.
      Lange Läufe deshalb mit `> log 2>&1` starten.
    - Es wird auf das Ende von bash gewartet. Hintergrundprozesse laufen danach
      weiter, ihre spätere Ausgabe wird nicht mehr eingesammelt.
    - Jeder Befehl bekommt eine eigene Prozessgruppe (nicht die des Servers).
      Beim Timeout wird die ganze Gruppe beendet. Mit `setsid` Gestartetes
      überlebt.
    """

    async def run(
        self,
        cmd: str,
        cwd: Path,
        timeout: int = 60,
        env: dict | None = None,
    ) -> LaunchResult:
        cwd.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(cwd),
                env=env,
                executable=_BASH,
                stdout=out,
                stderr=err,
                start_new_session=True,
            )
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                _kill_group(proc.pid)
                await proc.wait()
                return LaunchResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Timeout nach {timeout}s",
                    timed_out=True,
                )
            return LaunchResult(
                exit_code=proc.returncode or 0,
                stdout=_read(out),
                stderr=_read(err),
            )


_default: Launcher = DevLauncher()


def get_launcher() -> Launcher:
    return _default


def set_launcher(launcher: Launcher) -> None:
    global _default
    _default = launcher
