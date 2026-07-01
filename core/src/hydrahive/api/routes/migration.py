"""Server-zu-Server-Migration (Voll-Klon per rsync) — analog Bridge/Voice-Pattern.

`POST /api/admin/migration/start` validiert die Ziel-Angaben, legt das SSH-Passwort
in einer separaten 0600-Secret-Datei ab und schreibt einen Trigger-File. Ein
systemd-Timer (hydrahive2-migration.timer) pollt den Trigger und startet
hydrahive2-migration.service (oneshot, root), der `installer/migrate.sh` ausführt:
rsync -aAX --delete über SSH zum Zielserver. Live-Log via `/api/admin/migration/log`.

Das Passwort steht NIE in der Prozessliste (rsync/ssh lesen es via sshpass -f Datei)
und NIE im Log. Der Core-Service selbst führt kein rsync/ssh aus (läuft als
unprivilegierter `hydrahive`-User, kann root-owned Daten wie vms/ nicht lesen).
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/admin/migration", tags=["admin"])

TRIGGER = settings.data_dir / ".migration_request"
SECRET = settings.data_dir / ".migration_secret"
DONE_MARKER = settings.data_dir / ".migration_done"

# Hostname/IP: Buchstaben, Ziffern, Punkt, Bindestrich, Doppelpunkt (IPv6).
_HOST_RE = re.compile(r"^[A-Za-z0-9._:-]{1,253}$")
# SSH-User: konservativ, keine Shell-Metazeichen.
_USER_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


class MigrationStart(BaseModel):
    host: str = Field(..., description="Ziel-Host oder IP")
    port: int = Field(22, ge=1, le=65535)
    ssh_user: str = Field("root", description="SSH-User auf dem Ziel")
    password: str = Field(..., min_length=1, description="SSH-Passwort des Ziel-Users")
    bwlimit_kbps: int = Field(0, ge=0, description="Bandbreiten-Limit in KB/s (0=aus)")


def _is_running() -> bool:
    """Läuft gerade eine Migration? Trigger existiert oder Service aktiv."""
    return TRIGGER.exists() or SECRET.exists()


@router.get("/status")
def migration_status(_: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    running = _is_running()
    done = None
    if DONE_MARKER.exists():
        try:
            done = json.loads(DONE_MARKER.read_text())
        except (OSError, ValueError):
            done = None
    return {"running": running, "last_result": done}


@router.post("/start")
def migration_start(
    body: MigrationStart,
    _: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    if _is_running():
        raise coded(status.HTTP_409_CONFLICT, "migration_already_running")

    host = body.host.strip()
    if not _HOST_RE.match(host):
        raise coded(status.HTTP_400_BAD_REQUEST, "migration_invalid_host")
    if not _USER_RE.match(body.ssh_user):
        raise coded(status.HTTP_400_BAD_REQUEST, "migration_invalid_user")

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    DONE_MARKER.unlink(missing_ok=True)

    # Passwort in separate 0600-Datei — NICHT in den Klartext-Trigger, NICHT ins Log.
    # umask-sicher: erst 0600 anlegen, dann schreiben.
    fd = os.open(str(SECRET), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, body.password.encode())
    finally:
        os.close(fd)

    request = {
        "host": host,
        "port": body.port,
        "ssh_user": body.ssh_user,
        "bwlimit_kbps": body.bwlimit_kbps,
        "requested_at": int(time.time()),
    }
    TRIGGER.write_text(json.dumps(request))
    return {"started": True}


@router.get("/log")
def migration_log(
    _: Annotated[tuple[str, str], Depends(require_admin)],
    tail: int = 500,
) -> dict:
    log_path: Path = settings.migration_log_path
    if not log_path.exists():
        return {"exists": False, "lines": [], "running": _is_running()}
    lines = log_path.read_text(errors="replace").splitlines()[-tail:]
    return {
        "exists": True,
        "lines": [line + "\n" for line in lines],
        "running": _is_running(),
    }
