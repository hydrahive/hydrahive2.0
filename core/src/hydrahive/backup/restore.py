"""System-Backup-Restore mit Pre-Validate + Auto-Rollback.

Flow:
1. Validate (siehe validate.py)
2. Auto-Rollback-Backup vom aktuellen Stand erstellen
3. Tarball in temp-Dir extrahieren
4. Atomic-Replace Verzeichnis-für-Verzeichnis (alt → .old, neu → live, alt löschen)
5. DB-File atomic ersetzen
6. Restart-Trigger schreiben — systemd-path-Watcher übernimmt

Wenn Schritte 1-3 scheitern, bleibt der Live-Stand unverändert.
"""
from __future__ import annotations

import logging
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

from hydrahive.backup._paths import config_dir_arcname, data_subdirs, db_arcname
from hydrahive.backup.archive import create_system_archive
from hydrahive.backup.validate import RestoreError, validate_archive
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def restore_system_archive(archive_path: Path) -> dict:
    """Validiert, erstellt Auto-Rollback, ersetzt Live-Stand atomic."""
    manifest = validate_archive(archive_path)
    rollback = _create_rollback_backup()

    with tempfile.TemporaryDirectory(prefix="hh2-restore-") as tdir:
        extract_root = Path(tdir)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_root, filter="tar")

        for arcname, dst in data_subdirs():
            rel = arcname.split("/", 1)[1]
            src = extract_root / "data" / rel
            if src.exists():
                _atomic_replace_dir(src, dst)

        cfg_extract = extract_root / "config"
        if cfg_extract.exists():
            _atomic_replace_dir(cfg_extract, settings.config_dir)

        db_arc, db_dst = db_arcname()
        db_src = extract_root / db_arc
        if db_src.exists():
            db_dst.parent.mkdir(parents=True, exist_ok=True)
            db_src.replace(db_dst)

    _trigger_restart()
    return {"manifest": manifest, "rollback": str(rollback)}


def _create_rollback_backup() -> Path:
    """Sichert aktuellen Stand als Auto-Rollback bevor restored wird."""
    rollback_dir = settings.data_dir
    rollback = create_system_archive(rollback_dir)
    rollback_renamed = rollback_dir / f".backup-rollback-{int(time.time())}.tar.gz"
    rollback.rename(rollback_renamed)
    logger.warning("Auto-Rollback-Backup gespeichert: %s", rollback_renamed)
    return rollback_renamed


def _atomic_replace_dir(src: Path, dst: Path) -> None:
    """Verzeichnis-Replace: alten Pfad nach .old umbenennen, neuen rein, alten löschen.

    Nicht strikt atomic — wenn zwischen rename und Löschen abgebrochen wird,
    bleibt der .old-Pfad stehen und kann manuell wiederhergestellt werden.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        old = dst.with_suffix(dst.suffix + ".old-restore")
        if old.exists():
            shutil.rmtree(old, ignore_errors=True)
        dst.rename(old)
        try:
            shutil.move(str(src), str(dst))
        except OSError:
            old.rename(dst)
            raise
        shutil.rmtree(old, ignore_errors=True)
    else:
        shutil.move(str(src), str(dst))


def _trigger_restart() -> None:
    """Restart-Trigger schreiben — systemd-path nimmt's auf."""
    trigger = settings.data_dir / ".restart_request"
    try:
        trigger.write_text(str(int(time.time())))
        logger.warning("Restart-Trigger geschrieben (%s)", trigger)
    except OSError as e:
        logger.error("Restart-Trigger nicht schreibbar: %s", e)
