"""Lokale Bild-/Videogenerierung (ComfyUI) installieren und entfernen.

Muster wie Voice/Bridge: Die API schreibt nur eine Anfrage-Datei mit einem
festen Wort ("install" oder "uninstall"). hydrahive2-local-media.timer prüft
sie, hydrahive2-local-media.service führt als root
installer/local-media-ctl.sh aus und schreibt nach
/var/log/hydrahive2-local-media.log. Aus der GUI gelangen weder Pfade noch
Parameter in Shell-Code.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings
from hydrahive.system.local_media_status import get_status

router = APIRouter(
    prefix="/api/system/local-media",
    tags=["system"],
    dependencies=[Depends(require_admin)],
)

MAX_LOG_LINES = 1000
# Farbcodes der Installer-Skripte (log/warn/err färben ihre Ausgabe).
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# Pfade erst beim Aufruf auflösen, nicht beim Import: settings.data_dir ist
# eine cached_property, ein früher Zugriff würde den Wert festschreiben, bevor
# Tests oder der Dienst HH_DATA_DIR gesetzt haben.
def _trigger() -> Path:
    return settings.data_dir / ".local_media_request"


def _log_path() -> Path:
    return settings.local_media_log


def _request(action: str) -> dict:
    trigger = _trigger()
    if trigger.exists():
        raise coded(status.HTTP_409_CONFLICT, "local_media_busy")
    trigger.parent.mkdir(parents=True, exist_ok=True)
    trigger.write_text(action)
    return {"started": True}


@router.get("/status")
def local_media_status() -> dict:
    return {**get_status(), "running": _trigger().exists()}


@router.post("/install")
def install_local_media() -> dict:
    current = get_status()
    if not current["can_install"]:
        raise coded(
            status.HTTP_409_CONFLICT, "local_media_blocked",
            reason=current["blocked_reason"] or "already_installed",
        )
    return _request("install")


@router.post("/uninstall")
def uninstall_local_media() -> dict:
    if not get_status()["can_uninstall"]:
        raise coded(status.HTTP_409_CONFLICT, "local_media_not_installed")
    return _request("uninstall")


@router.get("/log")
def local_media_log(tail: int = 300) -> dict:
    log_path = _log_path()
    if not log_path.exists():
        return {"exists": False, "lines": []}
    try:
        text = _ANSI.sub("", log_path.read_text(encoding="utf-8", errors="replace"))
        lines = text.splitlines(keepends=True)
    except OSError as e:
        return {"exists": True, "lines": [], "error": str(e)}
    return {"exists": True, "lines": lines[-max(1, min(tail, MAX_LOG_LINES)):]}
