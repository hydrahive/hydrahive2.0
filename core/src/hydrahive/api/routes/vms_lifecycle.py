"""VM-Lifecycle: list, create, get, update, delete.

Per-User-Owner: Liste/Detail nur eigene VMs (außer Admin).
"""
from __future__ import annotations

import logging
import re
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vm_lifecycle_schemas import VMCreate, VMUpdate
from hydrahive.api.routes._vms_helpers import (
    is_admin, resolve_import_job, resolve_iso, serialize, vm_or_404,
)
from hydrahive.vms import db as vmdb
from hydrahive.vms import disk as vmdisk
from hydrahive.vms import import_job as vmimport
from hydrahive.vms import lifecycle
from hydrahive.vms.models import NAME_RE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vms", tags=["vms"])


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


@router.patch("/{vm_id}")
async def update_vm(
    vm_id: str,
    req: VMUpdate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    vm = vm_or_404(vm_id, *auth)
    if vm.actual_state not in ("stopped", "created", "error"):
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_must_be_stopped",
                    state=vm.actual_state)
    if req.name and req.name != vm.name and not re.match(NAME_RE, req.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_name_invalid", name=req.name)
    if req.name and req.name != vm.name and vmdb.name_taken(vm.owner, req.name, exclude_id=vm_id):
        raise coded(status.HTTP_409_CONFLICT, "vm_name_taken", name=req.name)
    if req.disk_gb is not None and req.disk_gb < vm.disk_gb:
        raise coded(status.HTTP_400_BAD_REQUEST, "vm_disk_shrink_not_supported",
                    current=vm.disk_gb, requested=req.disk_gb)

    iso_kw: dict = {}
    if req.clear_iso:
        iso_kw["iso_filename"] = None
    elif req.iso_filename is not None:
        if not resolve_iso(req.iso_filename):
            raise coded(status.HTTP_404_NOT_FOUND, "vm_iso_not_found", filename=req.iso_filename)
        iso_kw["iso_filename"] = req.iso_filename

    # Disk-Resize physisch BEVOR DB-Update — wenn das fehlschlägt soll DB konsistent bleiben
    if req.disk_gb is not None and req.disk_gb != vm.disk_gb:
        try:
            await vmdisk.grow_qcow2(vm_id, req.disk_gb)
        except vmdisk.DiskError as e:
            raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, e.code, **e.params)

    vmdb.update_vm_config(
        vm_id,
        name=req.name,
        description=req.description if req.description is not None else ...,
        cpu=req.cpu,
        ram_mb=req.ram_mb,
        disk_gb=req.disk_gb,
        **iso_kw,
    )
    return serialize(vmdb.get_vm(vm_id))


@router.delete("/{vm_id}", status_code=204)
async def delete_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    vm = vm_or_404(vm_id, *auth)
    if vm.actual_state in ("running", "starting"):
        await lifecycle.shutdown(vm_id, hard=True)
    vmdisk.remove_qcow2(vm_id)
    vmdb.delete_vm(vm_id)


