"""Bridge-Setup-Endpoints — analog Update/Voice-Pattern.

`POST /api/system/bridge/setup` schreibt einen Trigger-File. Ein
systemd-Timer (hydrahive2-bridge.timer) pollt das File und triggert
hydrahive2-bridge.service der `installer/setup-bridge.sh` als root
ausführt. Live-Log via `/api/system/bridge/log`.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/system/bridge", tags=["system"])

TRIGGER = settings.data_dir / ".bridge_setup_request"
LOG_PATH = Path("/var/log/hydrahive2-bridge.log")


@router.get("/status")
def bridge_status(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    ip_bin = shutil.which("ip") or "/sbin/ip"
    try:
        r = subprocess.run([ip_bin, "-br", "link", "show", "br0"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return {"installed": False}
    except Exception:
        return {"installed": False}
    parts = r.stdout.split()
    state = parts[1] if len(parts) > 1 else "?"
    addr = ""
    try:
        addr_r = subprocess.run([ip_bin, "-br", "-4", "addr", "show", "br0"],
                                capture_output=True, text=True, timeout=5)
        addr_parts = addr_r.stdout.split()
        addr = addr_parts[2] if len(addr_parts) > 2 else ""
    except Exception:
        pass
    return {"installed": True, "state": state, "ip": addr}


@router.post("/setup")
def bridge_setup(_: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    TRIGGER.write_text("1")
    return {"started": True}


@router.get("/log")
def bridge_log(
    _: Annotated[tuple[str, str], Depends(require_admin)],
    tail: int = 300,
) -> dict:
    if not LOG_PATH.exists():
        return {"exists": False, "lines": []}
    lines = LOG_PATH.read_text(errors="replace").splitlines()[-tail:]
    return {"exists": True, "lines": [l + "\n" for l in lines]}
