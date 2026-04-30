"""VM-Disk-Import: list, upload, from-path, delete.

qemu-img convert mit Progress-Parsing aus stderr läuft als BackgroundTask
ohne separaten Worker-Daemon.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import is_admin
from hydrahive.settings import settings
from hydrahive.vms import import_job as vmimport

router = APIRouter(prefix="/api/vms", tags=["vms"])


class ImportFromPath(BaseModel):
    source_path: str = Field(min_length=1, max_length=500)


@router.get("/import-jobs")
def list_import_jobs(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    return vmimport.db_list(owner=None if is_admin(role) else user)


@router.post("/import-jobs/upload", status_code=202)
async def import_upload(
    background: BackgroundTasks,
    disk: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Streamt Upload nach vms_dir/imports-tmp/<jobid>.<ext>, startet Convert."""
    user, _ = auth
    settings.vms_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = settings.vms_dir / "imports-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    job_id = "import-" + str(int(asyncio.get_event_loop().time() * 1000))
    src_name = (disk.filename or "upload.bin").replace("/", "_").replace("\\", "_")
    src_path = tmp_dir / f"{job_id}_{src_name}"
    target = settings.vms_disks_dir / f"{job_id}.qcow2"

    total = 0
    try:
        with src_path.open("wb") as f:
            while True:
                buf = await disk.read(1024 * 1024)
                if not buf:
                    break
                total += len(buf)
                f.write(buf)
    except OSError as e:
        src_path.unlink(missing_ok=True)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "import_upload_failed",
                    error=str(e))

    job_id_db = vmimport.db_create_job(user, str(src_path), str(target), bytes_total=total)
    background.add_task(vmimport.execute_job, job_id_db)
    return {"job_id": job_id_db}


@router.post("/import-jobs/from-path", status_code=202)
async def import_from_path(
    body: ImportFromPath, background: BackgroundTasks,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    if not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    src = Path(body.source_path)
    if not src.exists() or not src.is_file():
        raise coded(status.HTTP_400_BAD_REQUEST, "import_source_missing")
    job_id_str = "import-" + str(int(asyncio.get_event_loop().time() * 1000))
    target = settings.vms_disks_dir / f"{job_id_str}.qcow2"
    job_id_db = vmimport.db_create_job(user, str(src), str(target),
                                       bytes_total=src.stat().st_size)
    # cleanup_source=False — User-Datei bleibt bei from-path stehen
    async def _run():
        await vmimport.execute_job(job_id_db, cleanup_source=False)
    background.add_task(_run)
    return {"job_id": job_id_db}


@router.delete("/import-jobs/{job_id}", status_code=204)
def delete_import_job(
    job_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user, role = auth
    job = vmimport.db_get(job_id)
    if not job:
        raise coded(status.HTTP_404_NOT_FOUND, "import_job_not_found")
    if job["owner"] != user and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    if job["status"] == "done":
        target = Path(job["target_qcow2"])
        from hydrahive.db.connection import db as _db
        with _db() as conn:
            in_use = conn.execute(
                "SELECT 1 FROM vms WHERE qcow2_path = ?", (str(target),),
            ).fetchone()
        if not in_use:
            target.unlink(missing_ok=True)
    vmimport.db_delete(job_id)
