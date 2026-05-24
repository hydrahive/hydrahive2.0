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


def _add_dir(
    tar: tarfile.TarFile,
    arcname: str,
    source: Path,
    skipped: list[str],
) -> None:
    """Verzeichnis rekursiv ins Tar hinzufügen mit Exclude-Filter.

    Unlesbare Dateien (I/O-Fehler, z.B. Festplattenschaden) werden
    übersprungen und in `skipped` protokolliert statt den Backup abzubrechen.
    """
    if not source.exists():
        return
    try:
        items = list(source.rglob("*"))
    except OSError as e:
        logger.warning("rglob fehlgeschlagen für %s: %s", source, e)
        skipped.append(str(source))
        return
    for item in items:
        if is_excluded(item):
            continue
        rel = item.relative_to(source)
        try:
            tar.add(item, arcname=f"{arcname}/{rel}", recursive=False)
        except OSError as e:
            logger.warning("Datei übersprungen (I/O-Fehler): %s — %s", item, e)
            skipped.append(str(item))


def create_system_archive(target_dir: Path) -> Path:
    """Erstellt ein vollständiges System-Backup als .tar.gz.

    Returns absoluten Pfad zur fertigen .tar.gz-Datei.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_path = target_dir / f"hydrahive2-system-{timestamp}.tar.gz"
    tmp_db = target_dir / f".db-snapshot-{timestamp}.sqlite"

    skipped: list[str] = []

    try:
        if settings.sessions_db.exists():
            try:
                _checkpoint_db_to_tempfile(tmp_db)
            except OSError as e:
                logger.warning("DB-Checkpoint fehlgeschlagen, wird übersprungen: %s", e)
                skipped.append(str(settings.sessions_db))

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
                arc, _ = db_arcname()
                try:
                    tar.add(tmp_db, arcname=arc)
                except OSError as e:
                    logger.warning("DB aus Tar ausgelassen: %s", e)
                    skipped.append(str(tmp_db))

            for arc, source in data_subdirs():
                _add_dir(tar, arc, source, skipped)

            cfg_arc, cfg_src = config_dir_arcname()
            _add_dir(tar, cfg_arc, cfg_src, skipped)

            # Übersprungene Dateien separat protokollieren
            if skipped:
                _add_bytes(
                    tar,
                    "skipped.json",
                    json.dumps({"skipped_files": skipped}, indent=2).encode(),
                )

        if skipped:
            logger.warning(
                "Backup mit %d übersprungenen Dateien erstellt: %s",
                len(skipped), archive_path,
            )
        else:
            logger.info(
                "System-Backup erstellt: %s (%.1f MB)",
                archive_path, archive_path.stat().st_size / (1024 * 1024),
            )
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
