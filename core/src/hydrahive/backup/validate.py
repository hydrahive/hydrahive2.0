"""Tarball-Validation vor Restore.

Liest Manifest und prüft die mitgelieferte SQLite-DB auf Integrität, BEVOR
auf dem Live-System irgendetwas ausgetauscht wird.
"""
from __future__ import annotations

import json
import sqlite3
import tarfile
import tempfile
from pathlib import Path

from hydrahive.backup._paths import db_arcname

ARCHIVE_VERSION = "1"
MANIFEST_NAME = "manifest.json"


class RestoreError(Exception):
    def __init__(self, code: str, **params):
        self.code = code
        self.params = params
        super().__init__(code)


def validate_archive(archive_path: Path) -> dict:
    """Liest Manifest und prüft SQLite-Integrität. Wirft RestoreError bei Bug."""
    if not archive_path.exists():
        raise RestoreError("backup_archive_missing")

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            manifest = _read_manifest(tar)
            db_arc, _ = db_arcname()
            try:
                tar.getmember(db_arc)
            except KeyError:
                pass  # DB optional — fresh-install backup hätte keine
            else:
                _check_sqlite_in_tar(tar, db_arc)
    except tarfile.TarError as e:
        raise RestoreError("backup_tar_corrupt", error=str(e))
    return manifest


def _read_manifest(tar: tarfile.TarFile) -> dict:
    try:
        mf_member = tar.getmember(MANIFEST_NAME)
    except KeyError:
        raise RestoreError("backup_manifest_missing")
    mf_file = tar.extractfile(mf_member)
    if not mf_file:
        raise RestoreError("backup_manifest_unreadable")
    try:
        manifest = json.loads(mf_file.read().decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RestoreError("backup_manifest_invalid")

    if manifest.get("version") != ARCHIVE_VERSION:
        raise RestoreError("backup_version_unsupported",
                           version=str(manifest.get("version")))
    if manifest.get("kind") != "system":
        raise RestoreError("backup_kind_mismatch", kind=str(manifest.get("kind")))
    return manifest


def _check_sqlite_in_tar(tar: tarfile.TarFile, db_arc: str) -> None:
    """DB aus dem Tar in temp-File extrahieren und PRAGMA integrity_check laufen."""
    member = tar.getmember(db_arc)
    fileobj = tar.extractfile(member)
    if not fileobj:
        raise RestoreError("backup_db_unreadable")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp:
        tmp.write(fileobj.read())
        tmp_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(str(tmp_path))
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                raise RestoreError("backup_db_corrupt", detail=str(row))
        finally:
            conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)
