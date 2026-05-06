"""System-Samba — Status, Setup-Trigger, Login-Anzeige.

Setup-Trigger schreibt eine Datei die ein systemd-Service als root aufgreift
(analog Bridge/Voice-Pattern). Setup installiert Samba, legt den HH_SAMBA_USER
mit autogeneriertem Passwort an, schreibt smb.conf-Header mit
`include = $HH_SAMBA_INCLUDES_DIR`.
"""
from __future__ import annotations

import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from fastapi import APIRouter

from hydrahive.api.middleware.auth import require_admin
from hydrahive.samba.manager import samba_status
from hydrahive.settings import settings

router = APIRouter(prefix="/api/system/samba", tags=["system"])

TRIGGER = settings.data_dir / ".samba_setup_request"
LOG_PATH = settings.samba_log_path


@router.get("/status", dependencies=[Depends(require_admin)])
def status() -> dict:
    s = samba_status()
    pwd = ""
    if s["password_set"]:
        try:
            pwd = settings.samba_password_file.read_text().strip()
        except OSError:
            pwd = ""
    return {**s, "password": pwd}


@router.post("/setup", dependencies=[Depends(require_admin)])
def setup() -> dict:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    if not settings.samba_password_file.exists():
        settings.samba_password_file.write_text(secrets.token_urlsafe(18))
        settings.samba_password_file.chmod(0o600)
    TRIGGER.write_text("1")
    return {"started": True}


@router.get("/log", dependencies=[Depends(require_admin)])
def log_(tail: int = 200) -> dict:
    if not LOG_PATH.exists():
        return {"exists": False, "lines": []}
    lines = LOG_PATH.read_text(errors="replace").splitlines()[-tail:]
    return {"exists": True, "lines": [line + "\n" for line in lines]}
