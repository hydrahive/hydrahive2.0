"""System-Archiv einrichten – automatisch, ohne root, ohne Installer (Spec archiv-system.md).

Läuft beim Start des Dienstes und bei jedem Status-Aufruf des Admin-Fensters. Idempotent: Ordner
anlegen, Samba-Freigabe schreiben bzw. entfernen, _index.conf nur bei Bedarf neu. Wirft nie – der
Dienst muss auch starten, wenn die Platte fehlt oder Samba kaputt ist; der Grund steht im Ergebnis.
"""
from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

from hydrahive.archive import location
from hydrahive.archive._paths import KINDS, TRASH_DIR
from hydrahive.archive.share import render_share, share_conf_path
from hydrahive.samba import manager as samba_manager
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

DIR_MODE = 0o2775


def _ensure_folders(root: Path) -> None:
    for d in (root, *(root / k for k in (*KINDS, TRASH_DIR))):
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            os.chmod(d, DIR_MODE)


def _make_group_writable(path: Path) -> None:
    """Nur eigene Dateien; fremde (z. B. root-eigene) lassen wir in Ruhe."""
    try:
        if path.stat().st_uid == os.geteuid():
            os.chmod(path, stat.S_IMODE(path.stat().st_mode) | 0o664)
    except OSError as e:
        logger.warning("Rechte für %s nicht angepasst: %s", path, e)


def _index_has_share(inc: Path) -> bool:
    try:
        return f"include = {share_conf_path()}" in (inc / "_index.conf").read_text().splitlines()
    except OSError:
        return False


def _sync_share(root: Path) -> str:
    inc = Path(settings.samba_includes_dir)
    if not inc.is_dir():
        return "no_samba"
    conf = share_conf_path()
    if location.share_wanted():
        wanted = render_share(root)
        current = conf.read_text() if conf.is_file() else None
        if current != wanted:
            tmp = conf.with_name(conf.name + ".tmp")
            tmp.write_text(wanted)
            os.replace(tmp, conf)
            _make_group_writable(conf)
            logger.info("Samba-Freigabe des Archivs geschrieben: %s → %s", conf, root)
        if current != wanted or not _index_has_share(inc):
            samba_manager._regenerate_index()
            _make_group_writable(inc / "_index.conf")
        return "on"
    if conf.is_file() or _index_has_share(inc):
        conf.unlink(missing_ok=True)
        samba_manager._regenerate_index()
        _make_group_writable(inc / "_index.conf")
        logger.info("Samba-Freigabe des Archivs ausgeschaltet")
    return "off"


def ensure_archive() -> dict:
    root = location.archive_root()
    try:
        _ensure_folders(root)
    except OSError as e:
        logger.warning("Archiv-Ordner %s nicht anlegbar: %s", root, e)
        return {"folder": False, "share": "skipped", "error": str(e)}
    try:
        return {"folder": True, "share": _sync_share(root)}
    except OSError as e:
        logger.warning("Samba-Freigabe des Archivs nicht einrichtbar: %s", e)
        return {"folder": True, "share": "error", "error": str(e)}
