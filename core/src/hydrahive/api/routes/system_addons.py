"""Zusatz-Module im Admin-Cockpit nachinstallieren (docs/specs/installer-core-first.md §3).

Die API schreibt nur eine Anfrage-Datei mit genau einer Zeile „install <modul>“ (feste Liste, _addon_request.py).
hydrahive2-addon.timer prüft sie, hydrahive2-addon.service führt als root installer/addon-ctl.sh aus und schreibt nach
/var/log/hydrahive2-addon.log. Die Datei bleibt bis zum Ende liegen: so meldet die API „läuft“ und lehnt weitere
Aufträge ab. Aus der Oberfläche gelangen weder Pfade noch Parameter in Shell-Code.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._addon_request import request_install, running_addon, trigger_path
from hydrahive.settings import settings
from hydrahive.system.addons_status import ADDONS, list_addons

router = APIRouter(prefix="/api/system/addons", tags=["system"], dependencies=[Depends(require_admin)])

MAX_LOG_LINES = 1000
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# Pfade erst beim Aufruf auflösen (settings.* sind cached_property, siehe system_local_media.py).
def _trigger() -> Path:
    return trigger_path()


def _log_path() -> Path:
    return settings.log_dir / "hydrahive2-addon.log"


def _install_conf() -> Path:
    return settings.config_dir / "install.conf"


@router.get("")
def addons() -> dict:
    return {"items": list_addons(_install_conf()), "running": running_addon(_trigger())}


@router.post("/{addon}/install", status_code=status.HTTP_202_ACCEPTED)
def install_addon(addon: str) -> dict:
    if addon not in ADDONS:
        raise coded(status.HTTP_400_BAD_REQUEST, "addon_unknown", addon=addon[:32])
    current = {i["id"]: i for i in list_addons(_install_conf())}
    if current[addon]["hint"] == "mac":
        raise coded(status.HTTP_400_BAD_REQUEST, "addon_unavailable_mac", addon=addon)
    if current[addon]["installed"]:
        raise coded(status.HTTP_409_CONFLICT, "addon_installed", addon=addon)
    request_install(addon, _trigger())
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
