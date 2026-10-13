"""Samba-Freigabe des System-Archivs (nur Lesen des Zustands).

Angelegt wird sie vom Installer (installer/lib/archive-share.sh), weil dafür
smb.conf und Rechte am Archiv-Ordner nötig sind. Der Dateiname muss mit
dem Installer übereinstimmen.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings

SHARE_CONF_NAME = "_system-archiv.conf"


def share_conf_path() -> Path:
    return Path(settings.samba_includes_dir) / SHARE_CONF_NAME


def archive_share_enabled() -> bool:
    return share_conf_path().is_file()
