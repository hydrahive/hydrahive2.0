"""Extensions — Subprocess-Streaming für Install-Scripts und Docker-Compose."""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import AsyncIterator


async def stream_script(script_path: Path, env: dict[str, str] | None = None) -> AsyncIterator[str]:
    import shlex
    import tempfile
    full_env = {**os.environ, **(env or {})}
    wrapper_path: Path | None = None

    if os.getuid() == 0:
        cmd = ["/bin/bash", str(script_path)]
    elif env:
        # sudo strippt env-Vars — Temp-Wrapper-Script das Vars exportiert
        # und dann das echte Script ausführt. Nur /bin/bash ist in sudoers.
        lines = ["#!/bin/bash"]
        for k, v in env.items():
            lines.append(f"export {k}={shlex.quote(v)}")
        lines.append(f"exec /bin/bash {shlex.quote(str(script_path))}")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, dir="/tmp", prefix="hh-ext-"
        ) as f:
            f.write("\n".join(lines) + "\n")
            wrapper_path = Path(f.name)
        os.chmod(wrapper_path, 0o700)
        cmd = ["sudo", "-n", "/bin/bash", str(wrapper_path)]
    else:
        cmd = ["sudo", "-n", "/bin/bash", str(script_path)]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=full_env,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\n")
        await proc.wait()
        if proc.returncode != 0:
            yield f"[FEHLER] Script beendet mit Code {proc.returncode}"
        else:
            yield "[OK] Abgeschlossen"
    finally:
        if wrapper_path and wrapper_path.exists():
            wrapper_path.unlink(missing_ok=True)


async def stream_docker(
    compose_file: Path,
    action: str,
    env: dict[str, str] | None = None,
) -> AsyncIterator[str]:
    """action: 'up', 'down', 'start', 'stop', 'restart'"""
    import tempfile

    env_file: Path | None = None
    try:
        if action == "up":
            # Env-Variablen in temp .env-Datei schreiben — sudo strippt subprocess-env
            if env:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".env", delete=False, dir="/tmp"
                )
                for k, v in env.items():
                    tmp.write(f"{k}={v}\n")
                tmp.close()
                env_file = Path(tmp.name)
                os.chmod(env_file, 0o600)
                cmd = ["docker", "compose", "-f", str(compose_file),
                       "--env-file", str(env_file), "up", "-d", "--pull", "always"]
            else:
                cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d", "--pull", "always"]

            # sysctl für unprivilegierte Container-Ports setzen
            try:
                sysctl_cmd = ["sysctl", "-w", "net.ipv4.ip_unprivileged_port_start=0"]
                if os.getuid() != 0:
                    sysctl_cmd = ["sudo", "-n"] + sysctl_cmd
                subprocess.run(sysctl_cmd, capture_output=True, timeout=5)
            except Exception:
                pass
        elif action == "down":
            # Leere .env damit compose keine Warnings über fehlende Variablen wirft
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, dir="/tmp")
            tmp.close()
            env_file = Path(tmp.name)
            cmd = ["docker", "compose", "-f", str(compose_file),
                   "--env-file", str(env_file), "down", "--volumes", "--remove-orphans"]
        else:
            # start | stop | restart — kein volumes-Flag, kein env nötig
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, dir="/tmp")
            tmp.close()
            env_file = Path(tmp.name)
            cmd = ["docker", "compose", "-f", str(compose_file),
                   "--env-file", str(env_file), action]

        if os.getuid() != 0:
            cmd = ["sudo", "-n"] + cmd

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\n")
        await proc.wait()
        if proc.returncode != 0:
            yield f"[FEHLER] Docker beendet mit Code {proc.returncode}"
        else:
            yield "[OK] Abgeschlossen"
    finally:
        if env_file and env_file.exists():
            env_file.unlink(missing_ok=True)
