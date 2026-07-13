"""SSE-Stream für Docker-Engine-Installation. Aufgerufen von extensions.py."""
from __future__ import annotations

import asyncio
import json
import logging
import os

from hydrahive.api.routes._extensions_status import reset_docker_cache

logger = logging.getLogger(__name__)


def _sudo(parts: list[str]) -> list[str]:
    return parts if os.getuid() == 0 else ["sudo", "-n"] + parts


async def _run(cmd: list[str]) -> tuple[int, list[str]]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert proc.stdout is not None
    lines = []
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        lines.append(line.decode("utf-8", errors="replace").rstrip())
    await proc.wait()
    return proc.returncode, lines


async def install_docker_engine_stream():
    """Stellt sicher dass Docker läuft — installiert nur wenn nötig.
    Yieldet SSE-Frames als Strings."""
    rc, _ = await _run(["which", "docker"])
    docker_binary = rc == 0

    if not docker_binary:
        yield f"data: {json.dumps({'line': 'Docker nicht gefunden — starte Installation…'})}\n\n"
        proc = await asyncio.create_subprocess_exec(
            *_sudo(["/bin/bash", "-c", "curl -fsSL https://get.docker.com | sh"]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield f"data: {json.dumps({'line': line.decode('utf-8', errors='replace').rstrip()})}\n\n"
        await proc.wait()
        if proc.returncode != 0:
            yield f"data: {json.dumps({'line': '[FEHLER] Docker-Installation fehlgeschlagen'})}\n\n"
            yield "data: {\"done\": true}\n\n"
            return
    else:
        yield f"data: {json.dumps({'line': 'Docker binary gefunden — prüfe Daemon…'})}\n\n"

    # Daemon starten + aktivieren
    yield f"data: {json.dumps({'line': 'Aktiviere und starte docker.service…'})}\n\n"
    rc, lines = await _run(_sudo(["systemctl", "enable", "--now", "docker"]))
    for l in lines:
        yield f"data: {json.dumps({'line': l})}\n\n"

    # Gruppe setzen damit hydrahive ohne sudo docker nutzen kann
    import pwd
    try:
        current_user = pwd.getpwuid(os.getuid()).pw_name if os.getuid() != 0 else "hydrahive"
        rc2, _ = await _run(_sudo(["usermod", "-aG", "docker", current_user]))
        if rc2 == 0:
            yield f"data: {json.dumps({'line': f'Benutzer {current_user} zur docker-Gruppe hinzugefügt'})}\n\n"
    except (OSError, KeyError):
        pass  # Gruppe-Setzen optional (kein usermod/pwd-Eintrag) — Setup läuft weiter

    reset_docker_cache()
    yield f"data: {json.dumps({'line': '[OK] Docker ist bereit'})}\n\n"
    yield "data: {\"done\": true}\n\n"
