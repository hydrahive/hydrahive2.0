"""VM-Snapshots: list, create, restore, delete (alle offline)."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import vm_or_404
from hydrahive.vms import snapshots as vmsnap

router = APIRouter(prefix="/api/vms", tags=["vms"])


class SnapshotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)


@router.get("/{vm_id}/snapshots")
def list_snapshots(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    vm_or_404(vm_id, *auth)
    return vmsnap.db_list(vm_id)


@router.post("/{vm_id}/snapshots", status_code=201)
async def create_snapshot(
    vm_id: str, body: SnapshotCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    vm = vm_or_404(vm_id, *auth)
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
    vm = vm_or_404(vm_id, *auth)
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
    vm = vm_or_404(vm_id, *auth)
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
