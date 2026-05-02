"""Container lifecycle + inspection routes (start / stop / restart / log / config / info)."""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._container_helpers import container_or_404
from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus
from hydrahive.containers import lifecycle
from fastapi import status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/containers", tags=["containers"])


@router.post("/{container_id}/start")
async def start_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    container_or_404(container_id, *auth)
    try:
        await lifecycle.start(container_id)
    except incus.IncusError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return asdict(cdb.get(container_id))  # type: ignore[arg-type]


@router.post("/{container_id}/stop")
async def stop_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    container_or_404(container_id, *auth)
    try:
        await lifecycle.stop(container_id, force=False)
    except incus.IncusError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return asdict(cdb.get(container_id))  # type: ignore[arg-type]


@router.post("/{container_id}/restart")
async def restart_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    container_or_404(container_id, *auth)
    try:
        await lifecycle.restart_(container_id)
    except incus.IncusError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, **e.params)
    return asdict(cdb.get(container_id))  # type: ignore[arg-type]


@router.get("/{container_id}/log")
async def container_log(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    c = container_or_404(container_id, *auth)
    return {"text": await incus.show_log(c.name)}


@router.get("/{container_id}/config")
async def container_config(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    c = container_or_404(container_id, *auth)
    return {"text": await incus.show_config(c.name)}


@router.get("/{container_id}/info")
async def container_info(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Live info from incus: status, CPU/memory, IP."""
    c = container_or_404(container_id, *auth)
    info = await incus.info(c.name)
    if not info:
        return {"alive": False}
    state = info.get("state") or {}
    network = state.get("network") or {}
    eth0 = network.get("eth0") or {}
    addrs = [a for a in eth0.get("addresses", []) if a.get("family") == "inet" and a.get("scope") == "global"]
    cpu = state.get("cpu") or {}
    mem = state.get("memory") or {}
    return {
        "alive": True,
        "status": state.get("status", "").lower(),
        "ipv4": addrs[0]["address"] if addrs else None,
        "cpu_usage_ns": cpu.get("usage", 0),
        "memory_bytes": mem.get("usage", 0),
        "memory_peak_bytes": mem.get("usage_peak", 0),
    }
