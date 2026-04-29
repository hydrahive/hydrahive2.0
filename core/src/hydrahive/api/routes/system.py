from __future__ import annotations

import logging
import platform
import sys
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._system_checks import (
    check_db_writable,
    check_disk,
    check_llm_configured,
    check_workspace_dir,
    count_agents,
    count_projects,
)
from hydrahive.db.connection import db
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

def _installer_path(rel: str) -> Path:
    """Resolves an installer script path: base_dir first, then repo root via __file__."""
    p = settings.base_dir / rel
    if p.exists():
        return p
    # dev fallback: __file__ = core/src/hydrahive/api/routes/system.py → 5 levels up = repo root
    return Path(__file__).resolve().parents[5] / rel


UPDATE_SCRIPT = _installer_path("installer/update.sh")
UPDATE_TRIGGER = settings.data_dir / ".update_request"
UPDATE_LOG = Path("/var/log/hydrahive2-update.log")
RESTART_TRIGGER = settings.data_dir / ".restart_request"
VOICE_SCRIPT = _installer_path("installer/modules/55-voice.sh")
VOICE_TRIGGER = settings.data_dir / ".voice_install_request"
VOICE_LOG = Path("/var/log/hydrahive2-voice.log")

_start_time: float = 0.0


def set_start_time() -> None:
    global _start_time
    _start_time = time.time()


@router.get("/info")
def info(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    db_path = settings.sessions_db
    db_size = db_path.stat().st_size if db_path.exists() else 0
    return {
        "version": "2.0.0",
        "started_at": _start_time,
        "uptime_seconds": max(0.0, time.time() - _start_time),
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
        "data_dir": str(settings.data_dir),
        "config_dir": str(settings.config_dir),
        "db_path": str(db_path),
        "db_size_bytes": db_size,
    }


@router.get("/stats")
def stats(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    with db() as conn:
        sessions_total = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        sessions_active = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE status = 'active'"
        ).fetchone()[0]
        messages_total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        compactions = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'compaction'"
        ).fetchone()[0]
        tool_calls = conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]
        tool_calls_ok = conn.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE status = 'success'"
        ).fetchone()[0]
        tool_calls_err = conn.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE status = 'error'"
        ).fetchone()[0]

    agents_count, agents_by_type = count_agents()
    projects_count, projects_active = count_projects()

    return {
        "agents": {"total": agents_count, "by_type": agents_by_type},
        "projects": {"total": projects_count, "active": projects_active},
        "sessions": {"total": sessions_total, "active": sessions_active},
        "messages": {"total": messages_total, "compactions": compactions},
        "tool_calls": {
            "total": tool_calls,
            "success": tool_calls_ok,
            "error": tool_calls_err,
            "success_rate": round(tool_calls_ok / tool_calls * 100, 1) if tool_calls else 0,
        },
    }


@router.get("/health")
def health(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return {
        "checks": [
            check_db_writable(),
            check_llm_configured(),
            check_workspace_dir(),
            check_disk(),
        ],
    }


@router.post("/update", dependencies=[Depends(require_admin)])
def trigger_update() -> dict:
    """Writes a trigger file that systemd-path watches.

    The hydrahive2-update.path unit (set up by installer 50-systemd.sh)
    triggers hydrahive2-update.service which runs update.sh as root.
    No sudo from inside the API process needed — works with
    NoNewPrivileges=true on the main service.

    Backend will be killed when update.sh restarts the service —
    frontend should poll /health until reachable again with a new commit.
    """
    if not UPDATE_SCRIPT.exists():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "update_script_missing")
    try:
        UPDATE_TRIGGER.write_text(str(int(time.time())))
    except OSError as e:
        logger.exception("Trigger-File konnte nicht geschrieben werden")
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "update_trigger_failed", message=str(e))
    logger.warning("Update-Trigger geschrieben (%s) — systemd-Path-Watcher übernimmt", UPDATE_TRIGGER)
    return {"started": True}


@router.post("/restart", dependencies=[Depends(require_admin)])
def trigger_restart() -> dict:
    """Schreibt eine Trigger-Datei, die ein systemd-Path-Watcher beobachtet.

    Production: hydrahive2-restart.path/.service starten den Service neu (root).
    Dev: dev-start.sh hat einen Watch-Loop der `systemctl --user restart`
    aufruft. Backend-Antwort kommt zurück bevor der Restart greift —
    Frontend pollt /health bis der Service wieder antwortet.
    """
    try:
        RESTART_TRIGGER.write_text(str(int(time.time())))
    except OSError as e:
        logger.exception("Restart-Trigger-File konnte nicht geschrieben werden")
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "restart_trigger_failed", message=str(e))
    logger.warning("Restart-Trigger geschrieben (%s)", RESTART_TRIGGER)
    return {"started": True}


@router.post("/install-voice", dependencies=[Depends(require_admin)])
def trigger_voice_install() -> dict:
    """Writes a trigger file that the hydrahive2-voice.timer watches.

    The service runs 55-voice.sh as root — installs Docker if needed,
    pulls Wyoming containers, starts STT (port 10300) + TTS (port 10200).
    """
    if not VOICE_SCRIPT.exists():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "voice_script_missing")
    try:
        VOICE_TRIGGER.write_text(str(int(time.time())))
    except OSError as e:
        logger.exception("Voice-Trigger-File konnte nicht geschrieben werden")
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "voice_trigger_failed", message=str(e))
    logger.info("Voice-Install-Trigger geschrieben (%s)", VOICE_TRIGGER)
    return {"started": True}


@router.get("/install-voice/log", dependencies=[Depends(require_admin)])
def voice_log(tail: int = 200) -> dict:
    """Reads the last N lines from the voice install log."""
    if not VOICE_LOG.exists():
        return {"lines": [], "exists": False}
    try:
        with VOICE_LOG.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (PermissionError, OSError) as e:
        return {"lines": [], "exists": True, "error": str(e)}
    capped = max(1, min(tail, 1000))
    return {"lines": lines[-capped:], "exists": True}


@router.get("/update/log", dependencies=[Depends(require_admin)])
def update_log(tail: int = 200) -> dict:
    """Reads the last N lines from the update log file."""
    if not UPDATE_LOG.exists():
        return {"lines": [], "exists": False}
    try:
        with UPDATE_LOG.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (PermissionError, OSError) as e:
        return {"lines": [], "exists": True, "error": str(e)}
    capped = max(1, min(tail, 1000))
    return {"lines": lines[-capped:], "exists": True}
