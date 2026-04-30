"""Admin-System-Backup + Restore.

Backup: erstellt Tar zuerst in temp-Dir, dann FileResponse mit Content-Length
(damit Browser-Progress-Bar funktioniert).

Restore: Multipart-Upload, Pre-Validate, Auto-Rollback, atomic Replace,
Service-Restart-Trigger.
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.backup.archive import create_system_archive
from hydrahive.backup.restore import restore_system_archive
from hydrahive.backup.validate import RestoreError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/backup", dependencies=[Depends(require_admin)])
def create_backup(background: BackgroundTasks) -> FileResponse:
    """Erstellt Backup-Archiv in temp-Dir und liefert es als File-Download.

    Temp-File wird nach erfolgreichem Send via BackgroundTask gelöscht.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="hh2-backup-"))
    try:
        archive = create_system_archive(tmp_dir)
    except OSError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.exception("Backup-Erzeugung fehlgeschlagen")
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_create_failed",
                    error=str(e))

    background.add_task(shutil.rmtree, tmp_dir, ignore_errors=True)
    return FileResponse(
        path=archive,
        filename=archive.name,
        media_type="application/gzip",
    )


@router.post("/restore", dependencies=[Depends(require_admin)])
async def restore_backup(
    archive: Annotated[UploadFile, File()],
) -> dict:
    """Restore aus Upload — Pre-Validate, Auto-Rollback, Replace, Restart-Trigger.

    Antwort kommt zurück BEVOR der Service neu startet (systemd-path-Watcher
    übernimmt). Frontend pollt /health bis Backend wieder antwortet.
    """
    if not archive.filename:
        raise coded(status.HTTP_400_BAD_REQUEST, "backup_filename_missing")

    tmp_dir = Path(tempfile.mkdtemp(prefix="hh2-restore-"))
    upload_path = tmp_dir / "upload.tar.gz"
    try:
        with upload_path.open("wb") as f:
            while True:
                chunk = await archive.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        try:
            result = restore_system_archive(upload_path)
        except RestoreError as e:
            raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
        except OSError as e:
            logger.exception("Restore-Replace fehlgeschlagen")
            raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_restore_failed",
                        error=str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "restored": True,
        "manifest": result["manifest"],
        "rollback_path": result["rollback"],
    }
