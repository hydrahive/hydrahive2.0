"""Samba-Papierkorb des System-Archivs leeren.

Was über die Freigabe gelöscht wird, legt Samba (vfs recycle) in
.papierkorb ab. Leeren nur auf ausdrücklichen Wunsch (Admin-Fenster mit
Bestätigungswort). Gelöscht wird ausschließlich innerhalb des Papierkorbs,
Symlinks werden entfernt, aber nie verfolgt.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from hydrahive.archive._paths import archive_root, trash_dir

logger = logging.getLogger(__name__)


def empty_trash() -> int:
    """Leert den Papierkorb. Gibt die freigegebenen Bytes zurück."""
    t = trash_dir()
    if not os.path.lexists(t):
        return 0
    if t.is_symlink() or not t.is_dir():
        raise ValueError("Papierkorb ist kein echter Ordner – nichts gelöscht")
    if t.resolve().parent != archive_root().resolve():
        raise ValueError("Papierkorb liegt außerhalb des Archivs – nichts gelöscht")
    freed = 0
    for child in list(t.iterdir()):
        freed += _remove(child)
    logger.info("Archiv-Papierkorb geleert: %d Bytes", freed)
    return freed


def _remove(path: Path) -> int:
    if path.is_symlink() or not path.is_dir():
        size = path.lstat().st_size
        path.unlink()
        return size
    size = 0
    for dirpath, _dirs, files in os.walk(path, followlinks=False):
        for f in files:
            try:
                size += (Path(dirpath) / f).lstat().st_size
            except OSError:
                pass
    shutil.rmtree(path)
    return size
