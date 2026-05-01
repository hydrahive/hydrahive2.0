"""Samba-Share pro Projekt aktivieren/deaktivieren.

Schreibt eine Config-Datei pro Projekt in settings.samba_includes_dir,
smb.conf inkludiert das Verzeichnis. smbd reload via subprocess (sudo via
sudoers oder als root — der Backend-Service hat die Rechte über die Bridge-
Pattern wie für Tailscale)."""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from hydrahive.projects._paths import workspace_path
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]")


def _safe_share_name(project_name: str, project_id: str) -> str:
    """Safe Samba share name — only alnum/underscore/dash. Fallback: id-prefix."""
    safe = _NAME_RE.sub("_", project_name.strip()).strip("_")
    if not safe or len(safe) > 50:
        return f"hh_{project_id[:8]}"
    return safe


def _config_path(project_id: str) -> Path:
    return settings.samba_includes_dir / f"{project_id}.conf"


def render_share(project_id: str, project_name: str) -> str:
    """Render einen Share-Block. Bei späterem Per-User-Refactor wird hier
    valid users statt = $samba_user dynamisch je nach Projekt-Members gesetzt."""
    name = _safe_share_name(project_name, project_id)
    path = workspace_path(project_id)
    user = settings.samba_user
    return f"""[{name}]
   comment = HydraHive Project: {project_name}
   path = {path}
   browseable = yes
   read only = no
   valid users = {user}
   force user = {user}
   create mask = 0664
   directory mask = 0775
"""


def _reload_smbd() -> bool:
    """smbd config reloaden. Failt leise wenn smbd nicht installiert."""
    smbcontrol = shutil.which("smbcontrol")
    if not smbcontrol:
        for cand in ("/usr/bin/smbcontrol", "/usr/sbin/smbcontrol"):
            if Path(cand).exists():
                smbcontrol = cand; break
    if not smbcontrol:
        return False
    try:
        subprocess.run([smbcontrol, "all", "reload-config"],
                       capture_output=True, timeout=10, check=False)
        return True
    except Exception as e:
        logger.warning("smbd reload fehlgeschlagen: %s", e)
        return False


def enable_share(project_id: str, project_name: str) -> tuple[bool, str]:
    if not settings.samba_includes_dir.exists():
        return False, "samba_not_installed"
    cfg = _config_path(project_id)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    try:
        cfg.write_text(render_share(project_id, project_name))
    except PermissionError:
        return False, "samba_no_write_access"
    _reload_smbd()
    return True, ""


def disable_share(project_id: str) -> tuple[bool, str]:
    cfg = _config_path(project_id)
    if cfg.exists():
        try:
            cfg.unlink()
        except PermissionError:
            return False, "samba_no_write_access"
        _reload_smbd()
    return True, ""


def is_share_enabled(project_id: str) -> bool:
    return _config_path(project_id).exists()


def share_name_for(project_id: str, project_name: str) -> str:
    return _safe_share_name(project_name, project_id)


def _find_smbd() -> str | None:
    """Finde smbd-Binary. Service-PATH hat oft kein /usr/sbin — also auch
    explizit dort nachschauen."""
    found = shutil.which("smbd") or shutil.which("samba")
    if found:
        return found
    for candidate in ("/usr/sbin/smbd", "/usr/local/sbin/smbd", "/sbin/smbd"):
        if Path(candidate).exists():
            return candidate
    return None


def samba_status() -> dict:
    smbd_bin = _find_smbd()
    installed = bool(smbd_bin)
    running = False
    if installed:
        try:
            r = subprocess.run(["systemctl", "is-active", "smbd"],
                               capture_output=True, text=True, timeout=5)
            running = r.stdout.strip() == "active"
        except Exception:
            pass
    return {
        "installed": installed,
        "running": running,
        "user": settings.samba_user,
        "password_set": settings.samba_password_file.exists(),
        "includes_dir": str(settings.samba_includes_dir),
        "includes_dir_exists": settings.samba_includes_dir.exists(),
    }
