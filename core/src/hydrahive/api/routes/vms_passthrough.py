"""Passthrough-Disk-Routes — nur Admins."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import vm_or_404
from hydrahive.vms import passthrough as pt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vms", tags=["vms"])


def _serialize_disk(d: pt.PassthroughDisk) -> dict:
    return {
        "passthrough_id": d.passthrough_id,
        "vm_id": d.vm_id,
        "device_path": d.device_path,
        "label": d.label,
        "added_at": d.added_at,
    }


def _serialize_host_disk(d: pt.HostDisk) -> dict:
    return {
        "name": d.name,
        "path": d.path,
        "size": d.size,
        "model": d.model,
        "serial": d.serial,
        "children": [_serialize_host_disk(c) for c in d.children],
    }


# Literal route → muss VOR /{vm_id}-Routen im Aggregator eingebunden werden.
@router.get("/host-disks")
async def get_host_disks(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    require_admin(auth)
    try:
        disks = await pt.list_unmounted_host_disks()
    except pt.PassthroughError as e:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, e.code, **e.params)
    attached = pt.list_all_paths()
    return {
        "disks": [_serialize_host_disk(d) for d in disks],
        "attached_paths": list(attached),
    }


@router.get("/{vm_id}/passthrough-disks")
def get_passthrough_disks(
    vm_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    require_admin(auth)
    vm_or_404(vm_id, *auth)
    return [_serialize_disk(d) for d in pt.list_for_vm(vm_id)]


class AddPassthroughBody(BaseModel):
    device_path: str
    label: str | None = None


@router.post("/{vm_id}/passthrough-disks", status_code=status.HTTP_201_CREATED)
async def add_passthrough_disk(
    vm_id: str,
    body: AddPassthroughBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    require_admin(auth)
    vm = vm_or_404(vm_id, *auth)
    if vm.actual_state not in ("stopped", "created", "error"):
        raise coded(status.HTTP_409_CONFLICT, "vm_must_be_stopped")
    try:
        disk = await pt.add(vm_id, body.device_path, body.label)
    except pt.PassthroughError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return _serialize_disk(disk)


@router.delete("/{vm_id}/passthrough-disks/{passthrough_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def remove_passthrough_disk(
    vm_id: str,
    passthrough_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    require_admin(auth)
    vm = vm_or_404(vm_id, *auth)
    if vm.actual_state not in ("stopped", "created", "error"):
        raise coded(status.HTTP_409_CONFLICT, "vm_must_be_stopped")
    try:
        pt.remove(vm_id, passthrough_id)
    except pt.PassthroughError as e:
        raise coded(status.HTTP_404_NOT_FOUND, e.code, **e.params)
