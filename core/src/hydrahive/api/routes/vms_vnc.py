"""VNC-Token-Lookup für noVNC im Frontend.

websockify ist hinter nginx /vnc-ws/ gemounted (siehe 60-nginx.sh).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._vms_helpers import vm_or_404

router = APIRouter(prefix="/api/vms", tags=["vms"])


@router.get("/{vm_id}/vnc")
def vnc_info(vm_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    vm = vm_or_404(vm_id, *auth)
    if vm.actual_state != "running" or not vm.vnc_token:
        raise coded(status.HTTP_409_CONFLICT, "vm_not_running")
    return {"token": vm.vnc_token, "ws_path": "/vnc-ws/"}
