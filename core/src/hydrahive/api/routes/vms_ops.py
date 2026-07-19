"""VM runtime operation routes (start / stop / poweroff / stats / log)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware import users
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import ensure_local_vm, serialize, vm_or_404
from hydrahive.settings import settings
from hydrahive.vms import db as vmdb
from hydrahive.vms import execution as vmexec
from hydrahive.vms import lifecycle
from hydrahive.vms import remote as vmremote
from hydrahive.vms import stats as vmstats
from fastapi import status


def _actor_id(username: str) -> str:
    actor = users.get_by_username(username)
    return actor["user_id"] if actor is not None else username

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vms", tags=["vms"])


@router.post("/{vm_id}/start")
async def start_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    if vmexec.is_remote(vm):
        try:
            await vmexec.start(vm_id, actor=_actor_id(auth[0]))
        except vmremote.RemoteVMError as e:
            raise coded(status.HTTP_409_CONFLICT, "vm_remote_unavailable", reason=str(e))
        return serialize(vmdb.get_vm(vm_id))
    try:
        await lifecycle.start(vm_id)
    except lifecycle.VMLifecycleError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return serialize(vmdb.get_vm(vm_id))


@router.post("/{vm_id}/stop")
async def stop_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    if vmexec.is_remote(vm):
        try:
            await vmexec.stop(vm_id, actor=_actor_id(auth[0]), hard=False)
        except vmremote.RemoteVMError as e:
            raise coded(status.HTTP_409_CONFLICT, "vm_remote_unavailable", reason=str(e))
        return serialize(vmdb.get_vm(vm_id))
    try:
        await lifecycle.shutdown(vm_id, hard=False)
    except lifecycle.VMLifecycleError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return serialize(vmdb.get_vm(vm_id))


@router.post("/{vm_id}/poweroff")
async def poweroff_vm(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    if vmexec.is_remote(vm):
        try:
            await vmexec.stop(vm_id, actor=_actor_id(auth[0]), hard=True)
        except vmremote.RemoteVMError as e:
            raise coded(status.HTTP_409_CONFLICT, "vm_remote_unavailable", reason=str(e))
        return serialize(vmdb.get_vm(vm_id))
    try:
        await lifecycle.shutdown(vm_id, hard=True)
    except lifecycle.VMLifecycleError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return serialize(vmdb.get_vm(vm_id))


@router.get("/{vm_id}/stats")
def vm_stats(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    ensure_local_vm(vm)
    return vmstats.read_stats(vm.vm_id, vm.pid)


@router.get("/{vm_id}/log")
def vm_log(
    vm_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    tail: int = 200,
) -> dict:
    vm = vm_or_404(vm_id, *auth)
    ensure_local_vm(vm)
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
