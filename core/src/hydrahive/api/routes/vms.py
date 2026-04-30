"""VM-Management — REST-Routen.

Per-User-Owner: Liste/Detail nur eigene VMs (außer Admin), Create=eigener Owner.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.vms import db as vmdb
from hydrahive.vms import disk as vmdisk
from hydrahive.vms import import_job as vmimport
from hydrahive.vms import iso as vmiso
from hydrahive.vms import lifecycle
from hydrahive.vms import snapshots as vmsnap
from hydrahive.settings import settings
from hydrahive.vms.models import (
    MAX_CPU, MAX_DISK_GB, MAX_RAM_MB, MIN_CPU, MIN_DISK_GB, MIN_RAM_MB, NAME_RE,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vms", tags=["vms"])


class VMCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    cpu: int = Field(ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int = Field(ge=MIN_RAM_MB, le=MAX_RAM_MB)
    disk_gb: int = Field(ge=MIN_DISK_GB, le=MAX_DISK_GB)
    iso_filename: str | None = None
    network_mode: str = "bridged"


def _is_admin(role: str) -> bool:
    return role == "admin"


def _vm_or_404(vm_id: str, owner: str, role: str):
    vm = vmdb.get_vm(vm_id)
    if not vm:
        raise coded(status.HTTP_404_NOT_FOUND, "vm_not_found")
    if vm.owner != owner and not _is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    return vm


def _serialize(vm) -> dict:
    d = asdict(vm)
    return d


@router.get("")
def list_vms(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    vms = vmdb.list_vms(owner=None if _is_admin(role) else user)
    return [_serialize(v) for v in vms]


@router.post("", status_code=201)
async def create_vm(
    body: VMCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, _ = auth
    if not re.match(NAME_RE, body.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_name_invalid")
    if body.network_mode not in ("bridged", "isolated"):
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_network_mode_invalid")
    if vmdb.name_taken(user, body.name):
        raise coded(status.HTTP_409_CONFLICT, "vm_name_taken")

    if body.iso_filename:
        try:
            iso_safe = vmiso.safe_filename(body.iso_filename)
        except vmiso.ISOError as e:
            raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
        if not (vmiso.settings.vms_isos_dir / iso_safe).exists():
            raise coded(status.HTTP_400_BAD_REQUEST, "iso_not_found",
                        filename=body.iso_filename)
    else:
        iso_safe = None

    # 1. Disk anlegen, 2. dann DB-Eintrag — sonst hängen Orphan-DB-Zeilen
    vm = vmdb.create_vm(
        owner=user, name=body.name, description=body.description,
        cpu=body.cpu, ram_mb=body.ram_mb, disk_gb=body.disk_gb,
        iso_filename=iso_safe, network_mode=body.network_mode,
        qcow2_path="",  # wird gleich gesetzt
    )
    try:
        path = await vmdisk.create_qcow2(vm.vm_id, body.disk_gb)
    except vmdisk.DiskError as e:
        vmdb.delete_vm(vm.vm_id)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, e.code, **e.params)
    # qcow2_path nachträglich setzen
    from hydrahive.db.connection import db as _db
    with _db() as conn:
        conn.execute("UPDATE vms SET qcow2_path = ? WHERE vm_id = ?",
                     (str(path), vm.vm_id))
    return _serialize(vmdb.get_vm(vm.vm_id))


@router.get("/{vm_id}")
def get_vm_detail(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = _vm_or_404(vm_id, *auth)
    return _serialize(vm)


@router.delete("/{vm_id}", status_code=204)
async def delete_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    vm = _vm_or_404(vm_id, *auth)
    if vm.actual_state in ("running", "starting"):
        await lifecycle.shutdown(vm_id, hard=True)
    vmdisk.remove_qcow2(vm_id)
    vmdb.delete_vm(vm_id)


@router.post("/{vm_id}/start")
async def start_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _vm_or_404(vm_id, *auth)
    try:
        await lifecycle.start(vm_id)
    except lifecycle.VMLifecycleError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return _serialize(vmdb.get_vm(vm_id))


@router.post("/{vm_id}/stop")
async def stop_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _vm_or_404(vm_id, *auth)
    await lifecycle.shutdown(vm_id, hard=False)
    return _serialize(vmdb.get_vm(vm_id))


@router.post("/{vm_id}/poweroff")
async def poweroff_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _vm_or_404(vm_id, *auth)
    await lifecycle.shutdown(vm_id, hard=True)
    return _serialize(vmdb.get_vm(vm_id))


@router.get("/{vm_id}/vnc")
def vnc_info(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Liefert Token + WebSocket-Pfad für noVNC im Frontend.

    websockify ist im nginx hinter /vnc-ws/ gemounted (siehe 60-nginx.sh).
    """
    vm = _vm_or_404(vm_id, *auth)
    if vm.actual_state != "running" or not vm.vnc_token:
        raise coded(status.HTTP_409_CONFLICT, "vm_not_running")
    return {
        "token": vm.vnc_token,
        "ws_path": "/vnc-ws/",
    }


class SnapshotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)


@router.get("/{vm_id}/snapshots")
def list_snapshots(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    _vm_or_404(vm_id, *auth)
    return vmsnap.db_list(vm_id)


@router.post("/{vm_id}/snapshots", status_code=201)
async def create_snapshot(
    vm_id: str, body: SnapshotCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    vm = _vm_or_404(vm_id, *auth)
    if vm.actual_state != "stopped":
        raise coded(status.HTTP_409_CONFLICT, "snapshot_vm_not_stopped")
    try:
        size = await vmsnap.create(Path(vm.qcow2_path), body.name)
    except vmsnap.SnapshotError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    sid = vmsnap.db_create(vm_id, body.name, size, body.description)
    return vmsnap.db_get(sid) or {}


@router.post("/{vm_id}/snapshots/{snapshot_id}/restore", status_code=204)
async def restore_snapshot(
    vm_id: str, snapshot_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    vm = _vm_or_404(vm_id, *auth)
    if vm.actual_state != "stopped":
        raise coded(status.HTTP_409_CONFLICT, "snapshot_vm_not_stopped")
    snap = vmsnap.db_get(snapshot_id)
    if not snap or snap["vm_id"] != vm_id:
        raise coded(status.HTTP_404_NOT_FOUND, "snapshot_not_found")
    try:
        await vmsnap.restore(Path(vm.qcow2_path), snap["name"])
    except vmsnap.SnapshotError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)


@router.delete("/{vm_id}/snapshots/{snapshot_id}", status_code=204)
async def delete_snapshot(
    vm_id: str, snapshot_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    vm = _vm_or_404(vm_id, *auth)
    snap = vmsnap.db_get(snapshot_id)
    if not snap or snap["vm_id"] != vm_id:
        raise coded(status.HTTP_404_NOT_FOUND, "snapshot_not_found")
    if vm.actual_state != "stopped":
        raise coded(status.HTTP_409_CONFLICT, "snapshot_vm_not_stopped")
    try:
        await vmsnap.delete(Path(vm.qcow2_path), snap["name"])
    except vmsnap.SnapshotError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    vmsnap.db_delete(snapshot_id)


@router.get("/isos/list")
def list_isos(_: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    return [asdict(i) for i in vmiso.list_isos(with_hash=False)]


@router.post("/isos/upload", status_code=201)
async def upload_iso(
    iso: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    if not iso.filename:
        raise coded(status.HTTP_400_BAD_REQUEST, "iso_invalid_name", name="")
    try:
        result = await vmiso.save_upload_stream(iso.filename, iso)
    except vmiso.ISOError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return asdict(result)


class ImportFromPath(BaseModel):
    source_path: str = Field(min_length=1, max_length=500)


@router.get("/import-jobs")
def list_import_jobs(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    return vmimport.db_list(owner=None if _is_admin(role) else user)


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
    if not _is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    src = Path(body.source_path)
    if not src.exists() or not src.is_file():
        raise coded(status.HTTP_400_BAD_REQUEST, "import_source_missing")
    job_id_str = "import-" + str(int(asyncio.get_event_loop().time() * 1000))
    target = settings.vms_disks_dir / f"{job_id_str}.qcow2"
    job_id_db = vmimport.db_create_job(user, str(src), str(target),
                                       bytes_total=src.stat().st_size)
    # cleanup_source=False — bei from-path nicht löschen (User-Datei bleibt)
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
    if job["owner"] != user and not _is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    if job["status"] == "done":
        # qcow2 wegräumen wenn nicht in einer VM verwendet
        target = Path(job["target_qcow2"])
        from hydrahive.db.connection import db as _db
        with _db() as conn:
            in_use = conn.execute(
                "SELECT 1 FROM vms WHERE qcow2_path = ?", (str(target),),
            ).fetchone()
        if not in_use:
            target.unlink(missing_ok=True)
    vmimport.db_delete(job_id)


@router.delete("/isos/{filename}", status_code=204)
def delete_iso(
    filename: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user, role = auth
    if not _is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "vm_no_access")
    try:
        vmiso.delete_iso(filename)
    except vmiso.ISOError as e:
        raise coded(status.HTTP_404_NOT_FOUND, e.code, **e.params)
