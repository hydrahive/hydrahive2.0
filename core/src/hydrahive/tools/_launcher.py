from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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


class DevLauncher:
    """Spawns subprocesses as the service user inside `cwd`.

    This is the production launcher. Privilege-separation per Agent (systemd-run
    + dedicated users) is out of scope for Tills threat-model (home-lab, trusted
    agents with intentional full tool access — see CLAUDE.md).
    """

    async def run(
        self,
        cmd: str,
        cwd: Path,
        timeout: int = 60,
        env: dict | None = None,
    ) -> LaunchResult:
        cwd.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(cwd),
            env=env,
            executable=_BASH,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return LaunchResult(
                exit_code=-1,
                stdout="",
                stderr=f"Timeout nach {timeout}s",
                timed_out=True,
            )
        return LaunchResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )


_default: Launcher = DevLauncher()


def get_launcher() -> Launcher:
    return _default


def set_launcher(launcher: Launcher) -> None:
    global _default
    _default = launcher
