"""VM-Lifecycle: list, create, delete, start, stop, poweroff, stats, log, get-detail.

Per-User-Owner: Liste/Detail nur eigene VMs (außer Admin).
"""
from __future__ import annotations

import logging
import re
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import (
    resolve_import_job, resolve_iso, serialize, vm_or_404,
)
from hydrahive.settings import settings
from hydrahive.vms import db as vmdb
from hydrahive.vms import disk as vmdisk
from hydrahive.vms import import_job as vmimport
from hydrahive.vms import lifecycle
from hydrahive.vms import stats as vmstats
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
    # Wenn gesetzt: importiertes qcow2 wird übernommen statt neu erzeugt.
    # disk_gb wird dann ignoriert. Der Job-Eintrag wird beim Konsumieren gelöscht.
    import_job_id: str | None = None


@router.get("")
def list_vms(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    vms = vmdb.list_vms(owner=None if is_admin(role) else user)
    return [serialize(v) for v in vms]


@router.post("", status_code=201)
async def create_vm(
    body: VMCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    if not re.match(NAME_RE, body.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_name_invalid")
    if body.network_mode not in ("bridged", "isolated"):
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_network_mode_invalid")
    if vmdb.name_taken(user, body.name):
        raise coded(status.HTTP_409_CONFLICT, "vm_name_taken")

    iso_safe = resolve_iso(body.iso_filename)
    import_qcow2 = resolve_import_job(body.import_job_id, user, role)

    vm = vmdb.create_vm(
        owner=user, name=body.name, description=body.description,
        cpu=body.cpu, ram_mb=body.ram_mb, disk_gb=body.disk_gb,
        iso_filename=iso_safe, network_mode=body.network_mode,
        qcow2_path="",
    )
    try:
        if import_qcow2:
            target = vmdisk.disk_path_for(vm.vm_id)
            settings.vms_disks_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(import_qcow2), str(target))
            vmimport.db_delete(body.import_job_id)
            path = target
        else:
            path = await vmdisk.create_qcow2(vm.vm_id, body.disk_gb)
    except vmdisk.DiskError as e:
        vmdb.delete_vm(vm.vm_id)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, e.code, **e.params)
    except OSError as e:
        vmdb.delete_vm(vm.vm_id)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "import_move_failed",
                    error=str(e))
    from hydrahive.db.connection import db as _db
    with _db() as conn:
        conn.execute("UPDATE vms SET qcow2_path = ? WHERE vm_id = ?",
                     (str(path), vm.vm_id))
    return serialize(vmdb.get_vm(vm.vm_id))


@router.get("/{vm_id}")
def get_vm_detail(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    return serialize(vm)


@router.delete("/{vm_id}", status_code=204)
async def delete_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    vm = vm_or_404(vm_id, *auth)
    if vm.actual_state in ("running", "starting"):
        await lifecycle.shutdown(vm_id, hard=True)
    vmdisk.remove_qcow2(vm_id)
    vmdb.delete_vm(vm_id)


@router.post("/{vm_id}/start")
async def start_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm_or_404(vm_id, *auth)
    try:
        await lifecycle.start(vm_id)
    except lifecycle.VMLifecycleError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return serialize(vmdb.get_vm(vm_id))


@router.post("/{vm_id}/stop")
async def stop_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm_or_404(vm_id, *auth)
    await lifecycle.shutdown(vm_id, hard=False)
    return serialize(vmdb.get_vm(vm_id))


@router.post("/{vm_id}/poweroff")
async def poweroff_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm_or_404(vm_id, *auth)
    await lifecycle.shutdown(vm_id, hard=True)
    return serialize(vmdb.get_vm(vm_id))


@router.get("/{vm_id}/stats")
def vm_stats(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    return vmstats.read_stats(vm.vm_id, vm.pid)


@router.get("/{vm_id}/log")
def vm_log(
    vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)],
    tail: int = 200,
) -> dict:
    vm = vm_or_404(vm_id, *auth)
    log_path = settings.vms_logs_dir / f"{vm.vm_id}.log"
    if not log_path.exists():
        return {"lines": [], "exists": False}
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"lines": [], "exists": True, "error": str(e)}
    lines = text.splitlines()
    capped = max(1, min(tail, 2000))
    return {"lines": lines[-capped:], "exists": True}
