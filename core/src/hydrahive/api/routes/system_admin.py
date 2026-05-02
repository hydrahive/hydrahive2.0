"""System-Admin-Routen: Update, Restart, Voice-Install, Logs."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


def _installer_path(rel: str) -> Path:
    p = settings.base_dir / rel
    if p.exists():
        return p
    return Path(__file__).resolve().parents[5] / rel


UPDATE_SCRIPT = _installer_path("installer/update.sh")
UPDATE_TRIGGER = settings.data_dir / ".update_request"
UPDATE_LOG = settings.update_log
RESTART_TRIGGER = settings.data_dir / ".restart_request"
VOICE_SCRIPT = _installer_path("installer/modules/55-voice.sh")
VOICE_TRIGGER = settings.data_dir / ".voice_install_request"
VOICE_LOG = settings.voice_log


@router.get("/check-update", dependencies=[Depends(require_admin)])
async def check_update() -> dict:
    from hydrahive.api.version import refresh_update_status
    commit, behind = await refresh_update_status()
    return {"commit": commit, "update_behind": behind}


@router.post("/update", dependencies=[Depends(require_admin)])
def trigger_update() -> dict:
    if not UPDATE_SCRIPT.exists():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "update_script_missing")
    try:
        UPDATE_TRIGGER.write_text(str(int(time.time())))
    except OSError as e:
        logger.exception("Trigger-File konnte nicht geschrieben werden")
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "update_trigger_failed", message=str(e))
    logger.warning("Update-Trigger geschrieben (%s) — systemd-Path-Watcher übernimmt", UPDATE_TRIGGER)
    return {"started": True}


_RESTART_COOLDOWN_SEC = 60
_last_restart_trigger: float = 0.0


@router.post("/restart", dependencies=[Depends(require_admin)])
def trigger_restart() -> dict:
    """Cooldown: max 1 Restart pro 60s — verhindert Restart-Loops bei
    Click-Spam oder ungelöschtem Trigger-File."""
    global _last_restart_trigger
    now = time.time()
    elapsed = now - _last_restart_trigger
    if elapsed < _RESTART_COOLDOWN_SEC:
        wait = int(_RESTART_COOLDOWN_SEC - elapsed)
        raise coded(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "restart_cooldown_active",
            message=f"Bitte {wait}s warten — letzter Restart-Trigger ist zu kurz her.",
        )
    try:
        RESTART_TRIGGER.write_text(str(int(now)))
    except OSError as e:
        logger.exception("Restart-Trigger-File konnte nicht geschrieben werden")
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "restart_trigger_failed", message=str(e))
    _last_restart_trigger = now
    logger.warning("Restart-Trigger geschrieben (%s)", RESTART_TRIGGER)
    return {"started": True}


@router.post("/install-voice", dependencies=[Depends(require_admin)])
def trigger_voice_install() -> dict:
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
    if not UPDATE_LOG.exists():
        return {"lines": [], "exists": False}
    try:
        with UPDATE_LOG.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (PermissionError, OSError) as e:
        return {"lines": [], "exists": True, "error": str(e)}
    capped = max(1, min(tail, 1000))
    return {"lines": lines[-capped:], "exists": True}
