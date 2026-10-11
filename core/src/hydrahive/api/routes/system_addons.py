"""Zusatz-Module im Admin-Cockpit nachinstallieren (docs/specs/installer-core-first.md §3).

Die API schreibt nur eine Anfrage-Datei mit genau einer Zeile „install <modul>“ (feste Liste). hydrahive2-addon.timer
prüft sie, hydrahive2-addon.service führt als root installer/addon-ctl.sh aus und schreibt nach
/var/log/hydrahive2-addon.log. Die Datei bleibt bis zum Ende liegen: so meldet die API „läuft“ und lehnt weitere
Aufträge ab. Aus der Oberfläche gelangen weder Pfade noch Parameter in Shell-Code.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings
from hydrahive.system.addons_status import ADDONS, list_addons

router = APIRouter(prefix="/api/system/addons", tags=["system"], dependencies=[Depends(require_admin)])

MAX_LOG_LINES = 1000
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_REQUEST = re.compile(r"^install ([a-z]+)\s*$")


# Pfade erst beim Aufruf auflösen (settings.* sind cached_property, siehe system_local_media.py).
def _trigger() -> Path:
    return settings.data_dir / ".addon_request"


def _log_path() -> Path:
    return settings.log_dir / "hydrahive2-addon.log"


def _install_conf() -> Path:
    return settings.config_dir / "install.conf"


def running_addon() -> str | None:
    """Name des laufenden Auftrags oder None. Auch fremde Inhalte gelten als „läuft“ (Runner räumt sie weg)."""
    trigger = _trigger()
    try:
        text = trigger.read_text(errors="replace")[:64]
    except FileNotFoundError:
        return None
    except OSError:
        return "?"
    m = _REQUEST.match(text)
    return m.group(1) if m else "?"


def request_install(addon: str) -> None:
    """Auftrag schreiben. Wirft 400 (unbekannt) oder 409 (läuft schon). Auch von den alten Wegen benutzt."""
    if addon not in ADDONS:
        raise coded(status.HTTP_400_BAD_REQUEST, "addon_unknown", addon=addon[:32])
    if running_addon() is not None:
        raise coded(status.HTTP_409_CONFLICT, "addon_busy")
    trigger = _trigger()
    trigger.parent.mkdir(parents=True, exist_ok=True)
    trigger.write_text(f"install {addon}\n")


@router.get("")
def addons() -> dict:
    return {"items": list_addons(_install_conf()), "running": running_addon()}


@router.post("/{addon}/install", status_code=status.HTTP_202_ACCEPTED)
def install_addon(addon: str) -> dict:
    if addon not in ADDONS:
        raise coded(status.HTTP_400_BAD_REQUEST, "addon_unknown", addon=addon[:32])
    current = {i["id"]: i for i in list_addons(_install_conf())}
    if current[addon]["installed"]:
        raise coded(status.HTTP_409_CONFLICT, "addon_installed", addon=addon)
    request_install(addon)
    return {"started": True}


@router.get("/log")
def addon_log(tail: int = 300) -> dict:
    log_path = _log_path()
    if not log_path.exists():
        return {"exists": False, "lines": []}
    try:
        text = _ANSI.sub("", log_path.read_text(encoding="utf-8", errors="replace"))
    except OSError as e:
        return {"exists": True, "lines": [], "error": str(e)}
    lines = text.splitlines(keepends=True)
    return {"exists": True, "lines": lines[-max(1, min(tail, MAX_LOG_LINES)):]}
