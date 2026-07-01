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
import os
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

from hydrahive.backup._limits import enforce_archive_limits
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
            enforce_archive_limits(tar)  # Dekompressionsbomben-Schutz (#189)
            # filter="data" (nicht "tar") lehnt absolute/eskapierende Symlinks,
            # Hardlinks, Device-Nodes und setuid-Bits ab — Pflicht beim Restore
            # aus fremder Quelle (Issue #182, analog zu user_restore.py).
            tar.extractall(extract_root, filter="data")

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
    """Ersetzt das Zielverzeichnis durch ``src``.

    Bevorzugt der schnelle, atomare Verzeichnis-rename (altes → ``.old-restore``,
    neues rein, altes löschen). Der greift aber NICHT, wenn das Zielverzeichnis
    selbst nicht umbenannt werden kann:

    - ``config_dir`` = ``/etc/hydrahive2`` liegt in ``/etc`` (gehört root) → der
      Service-User darf dort nicht umbenennen (EPERM), UND
    - der systemd-Dienst richtet ``ReadWritePaths=/etc/hydrahive2 /var/lib/hydrahive2``
      als Bind-Mounts im Service-Namespace ein → das Verzeichnis IST ein
      Mount-Point und ``rename`` schlägt mit EBUSY fehl.

    In beiden Fällen wird der INHALT in-place ersetzt (Dateien im bestehenden
    Verzeichnis austauschen), statt das Verzeichnis selbst zu bewegen. Das umgeht
    Permission UND Bind-Mount, ohne sudo — alle Operationen laufen im
    user-eigenen Verzeichnis.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return

    old = dst.with_suffix(dst.suffix + ".old-restore")
    if _can_rename_dir(dst, old):
        # Schneller Pfad: Verzeichnis atomar tauschen.
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
        # Mount-Point / nicht umbenennbares Verzeichnis: Inhalt in-place ersetzen.
        _replace_dir_contents(src, dst)


def _can_rename_dir(dst: Path, probe: Path) -> bool:
    """Testet ohne Seiteneffekt, ob ``dst`` umbenannt werden kann (nicht Mount-
    Point, Elternpfad schreibbar). Benennt kurz um und sofort zurück."""
    if not os.access(dst.parent, os.W_OK):
        return False
    if probe.exists():
        return False
    try:
        dst.rename(probe)
    except OSError:
        return False
    try:
        probe.rename(dst)
    except OSError:
        # Rückbenennung scheiterte — extrem unwahrscheinlich; als nicht-renambar
        # behandeln, damit der Inhalts-Pfad übernimmt (dst liegt noch als probe).
        try:
            probe.rename(dst)
        except OSError:
            pass
        return False
    return True


def _replace_dir_contents(src: Path, dst: Path) -> None:
    """Ersetzt den Inhalt von ``dst`` durch den von ``src`` — Datei für Datei,
    ohne ``dst`` selbst zu bewegen (Mount-Point-/Permission-sicher).

    Auto-Rollback: alter Inhalt wandert erst in ein ``.old-restore/`` UNTERHALB
    von ``dst`` (gleiches Filesystem, umbenennbar), wird bei Erfolg gelöscht und
    bei Fehler zurückgeholt. Einträge, die der User nicht bewegen kann (fremd-
    owned wie root-eigene ``env``/``extensions``), werden übersprungen und bleiben
    unverändert erhalten — die sind hostspezifisch, nicht Teil eines portablen
    Restores (analog zum ``tls/``-Ausschluss im Backup)."""
    backup = dst / ".old-restore"
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    backup.mkdir(parents=True, exist_ok=True)

    backed_up: list[str] = []   # Namen, deren Original in backup/ liegt
    added: list[str] = []        # Namen, die wir neu in dst eingebracht haben
    skipped: list[str] = []
    try:
        # 1) bestehenden Inhalt (außer dem backup-Ordner) beiseite räumen
        for entry in list(dst.iterdir()):
            if entry == backup:
                continue
            try:
                entry.rename(backup / entry.name)
                backed_up.append(entry.name)
            except OSError:
                # Nicht bewegbar (fremd-owned, z.B. root:hydrahive env/extensions)
                # → unverändert lassen. Hostspezifisch, gehört nicht in den Restore.
                skipped.append(entry.name)

        # 2) neuen Inhalt hineinbringen (skip, was wir übersprungen haben)
        for entry in list(src.iterdir()):
            if entry.name in skipped:
                continue
            shutil.move(str(entry), str(dst / entry.name))
            added.append(entry.name)

        # 3) Erfolg → alten Inhalt löschen
        shutil.rmtree(backup, ignore_errors=True)
        if skipped:
            logger.warning(
                "config-Restore: %d hostspezifische Einträge übersprungen "
                "(fremd-owned, unverändert erhalten): %s",
                len(skipped), ", ".join(sorted(skipped)),
            )
    except Exception:
        # Rollback: erst neu eingebrachte Einträge raus, dann Originale zurück.
        for name in added:
            live = dst / name
            if live.is_dir():
                shutil.rmtree(live, ignore_errors=True)
            else:
                live.unlink(missing_ok=True)
        for name in backed_up:
            src_bak = backup / name
            if src_bak.exists():
                try:
                    src_bak.rename(dst / name)
                except OSError:
                    pass
        shutil.rmtree(backup, ignore_errors=True)
        raise


def _trigger_restart() -> None:
    """Restart-Trigger schreiben — systemd-path nimmt's auf."""
    trigger = settings.data_dir / ".restart_request"
    try:
        trigger.write_text(str(int(time.time())))
        logger.warning("Restart-Trigger geschrieben (%s)", trigger)
    except OSError as e:
        logger.error("Restart-Trigger nicht schreibbar: %s", e)
