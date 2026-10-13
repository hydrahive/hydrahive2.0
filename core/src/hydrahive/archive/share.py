"""Samba-Freigabe des System-Archivs: Block erzeugen und Zustand lesen.

Geschrieben wird sie von archive/setup.py – ohne root. Das Include-Verzeichnis hh-projects.d gehört
der Gruppe hydrahive (47-samba.sh), smbd liest neue Freigaben daraus für neue Verbindungen ohne Reload.
"""
from __future__ import annotations

import os
import pwd
from pathlib import Path

from hydrahive.settings import settings

SHARE_CONF_NAME = "_system-archiv.conf"
SHARE_NAME = "HydraHive_Archiv"


def share_conf_path() -> Path:
    return Path(settings.samba_includes_dir) / SHARE_CONF_NAME


def archive_share_enabled() -> bool:
    return share_conf_path().is_file()


def _service_user() -> str:
    """Eigentümer der Dateien, die über die Freigabe hineinkommen: der Dienst-Nutzer selbst."""
    try:
        return pwd.getpwuid(os.geteuid()).pw_name
    except KeyError:
        return "hydrahive"


def render_share(root: Path) -> str:
    """Lesen + schreiben, was übers Netz kommt gehört dem Dienst; Gelöschtes landet im Papierkorb."""
    owner = _service_user()
    return (
        "# HydraHive2 — System-Archiv (automatisch erzeugt von archive/setup.py)\n"
        f"[{SHARE_NAME}]\n"
        "   comment = HydraHive System-Archiv\n"
        f"   path = {root}\n"
        "   browseable = yes\n"
        "   read only = no\n"
        f"   valid users = {settings.samba_user}\n"
        f"   force user = {owner}\n"
        f"   force group = {owner}\n"
        "   create mask = 0664\n"
        "   directory mask = 2775\n"
        "   vfs objects = recycle\n"
        "   recycle:repository = .papierkorb\n"
        "   recycle:keeptree = yes\n"
        "   recycle:versions = yes\n"
        "   recycle:touch = yes\n"
        "   recycle:exclude_dir = .papierkorb\n"
    )
