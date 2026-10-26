"""Projekt-Freigabe auf dem Mac über die macOS-eigene Dateifreigabe (docs/plans/mac-file-sharing.md §2).

Das Backend läuft als Dienst-Konto ohne root und darf ``sharing`` nicht aufrufen. Es schreibt deshalb nur
Anfrage-Dateien ``<id>.want`` (Zeilen: on/off, Freigabename, Pfad) in ``$HH_CONFIG_DIR/mac-shares.d``; der
LaunchDaemon ``io.hydrahive.shares`` (root, ``installer/lib/mac-shares-ctl.sh``) prüft und setzt sie um und meldet
``<id>.state`` (on / off / error:<grund>). Freigabe-Konto: ``hhshare`` (ohne Login-Shell, nur SMB).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from hydrahive.settings import settings

SHARE_USER = "hhshare"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def shares_dir() -> Path:
    return settings.config_dir / "mac-shares.d"


def valid_project_id(project_id: str) -> bool:
    return bool(_ID_RE.match(project_id or ""))


def account_exists() -> bool:
    """Freigabe-Konto da? (vom Zusatz-Modul 47-filesharing.sh angelegt)"""
    dscl = shutil.which("dscl") or "/usr/bin/dscl"
    try:
        r = subprocess.run([dscl, ".", "-read", f"/Users/{SHARE_USER}", "UniqueID"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def smbd_running() -> bool:
    try:
        r = subprocess.run(["/usr/bin/pgrep", "-x", "smbd"], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def request(project_id: str, on: bool, share_name: str, path: Path) -> None:
    d = shares_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f".{project_id}.want.tmp"
    tmp.write_text(f"{'on' if on else 'off'}\n{share_name}\n{path}\n")
    tmp.replace(d / f"{project_id}.want")                 # erst vollständig, dann sichtbar (WatchPaths)


def state(project_id: str) -> str:
    try:
        return (shares_dir() / f"{project_id}.state").read_text().strip()
    except OSError:
        return ""


def status() -> dict:
    installed = account_exists()
    return {
        "installed": installed,
        "running": installed and smbd_running(),
        "user": SHARE_USER,
        "password_set": settings.samba_password_file.exists(),
        "includes_dir": str(shares_dir()),
        "includes_dir_exists": shares_dir().exists(),
        "platform": "mac",
    }
