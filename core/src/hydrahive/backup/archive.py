"""System-Backup-Archive erzeugen.

SQLite wird via .backup()-API in temp-File kopiert (atomic-safe trotz WAL-Mode).
Dann werden DB + Daten + Config in ein .tar.gz gepackt mit Manifest.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import tarfile
import time
from pathlib import Path

from hydrahive.backup._paths import (
    config_dir_arcname,
    data_subdirs,
    db_arcname,
    is_excluded,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

ARCHIVE_VERSION = "1"
MANIFEST_NAME = "manifest.json"


def _checkpoint_db_to_tempfile(target: Path) -> None:
    """SQLite-DB sauber kopieren mit sqlite3.backup-API. Verträgt WAL-Mode."""
    src = sqlite3.connect(str(settings.sessions_db))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _add_dir(tar: tarfile.TarFile, arcname: str, source: Path) -> None:
    """Verzeichnis rekursiv ins Tar hinzufügen mit Exclude-Filter."""
    if not source.exists():
        return
    for item in source.rglob("*"):
        if is_excluded(item):
            continue
        rel = item.relative_to(source)
        tar.add(item, arcname=f"{arcname}/{rel}", recursive=False)


def create_system_archive(target_dir: Path) -> Path:
    """Erstellt ein vollständiges System-Backup als .tar.gz.

    Returns absoluten Pfad zur fertigen .tar.gz-Datei.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_path = target_dir / f"hydrahive2-system-{timestamp}.tar.gz"
    tmp_db = target_dir / f".db-snapshot-{timestamp}.sqlite"

    try:
        if settings.sessions_db.exists():
            _checkpoint_db_to_tempfile(tmp_db)

        manifest = {
            "version": ARCHIVE_VERSION,
            "kind": "system",
            "created_at": timestamp,
            "hostname": _read_hostname(),
        }

        with tarfile.open(archive_path, "w:gz") as tar:
            # Manifest zuerst — damit der Validator es ohne komplettes
            # Auspacken lesen kann.
            _add_bytes(tar, MANIFEST_NAME, json.dumps(manifest, indent=2).encode())

            if tmp_db.exists():
                arcname, _ = db_arcname()
                tar.add(tmp_db, arcname=arcname)

            for arcname, source in data_subdirs():
                _add_dir(tar, arcname, source)

            cfg_arc, cfg_src = config_dir_arcname()
            _add_dir(tar, cfg_arc, cfg_src)

        logger.info("System-Backup erstellt: %s (%.1f MB)",
                    archive_path, archive_path.stat().st_size / (1024 * 1024))
        return archive_path
    finally:
        tmp_db.unlink(missing_ok=True)


def _add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    import io
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = int(time.time())
    tar.addfile(info, io.BytesIO(data))


def _read_hostname() -> str:
    try:
        return Path("/etc/hostname").read_text().strip() or "unknown"
    except OSError:
        return "unknown"
