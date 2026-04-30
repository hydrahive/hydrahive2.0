"""Container-Management — REST-Routen."""
from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus
from hydrahive.containers import lifecycle
from hydrahive.containers.models import (
    MAX_CPU, MAX_RAM_MB, MIN_CPU, MIN_RAM_MB, NAME_RE, QUICK_IMAGES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/containers", tags=["containers"])


class ContainerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    description: str | None = Field(default=None, max_length=500)
    image: str = Field(min_length=1, max_length=120)
    cpu: int | None = Field(default=None, ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int | None = Field(default=None, ge=MIN_RAM_MB, le=MAX_RAM_MB)
    network_mode: str = "bridged"


def _is_admin(role: str) -> bool:
    return role == "admin"


def _container_or_404(container_id: str, owner: str, role: str):
    c = cdb.get(container_id)
    if not c:
        raise coded(status.HTTP_404_NOT_FOUND, "container_not_found")
    if c.owner != owner and not _is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "container_no_access")
    return c


@router.get("")
def list_containers(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    cs = cdb.list_(owner=None if _is_admin(role) else user)
    return [asdict(c) for c in cs]


@router.get("/quick-images")
def quick_images(_: Annotated[tuple[str, str], Depends(require_auth)]) -> list[str]:
    return list(QUICK_IMAGES)


@router.post("", status_code=201)
async def create_container(
    body: ContainerCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, _ = auth
    if not re.match(NAME_RE, body.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_name_invalid")
    if body.network_mode not in ("bridged", "isolated"):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_network_mode_invalid")
    if cdb.name_taken(body.name):
        raise coded(status.HTTP_409_CONFLICT, "container_name_taken")
    if not incus.is_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "incus_missing")

    image = body.image.strip()
    if ":" not in image:
        image = f"images:{image}"

    c = cdb.create(
        owner=user, name=body.name, description=body.description,
        image=image, cpu=body.cpu, ram_mb=body.ram_mb,
        network_mode=body.network_mode,
    )
    try:
        await lifecycle.create_and_start(c.container_id)
    except incus.IncusError as e:
        cdb.delete(c.container_id)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, e.code, **e.params)
    return asdict(cdb.get(c.container_id))  # type: ignore[arg-type]


@router.get("/{container_id}")
def get_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    return asdict(_container_or_404(container_id, *auth))


@router.delete("/{container_id}", status_code=204)
async def delete_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    _container_or_404(container_id, *auth)
    await lifecycle.delete(container_id)


@router.post("/{container_id}/start")
async def start_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    _container_or_404(container_id, *auth)
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
    _container_or_404(container_id, *auth)
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
    _container_or_404(container_id, *auth)
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
    c = _container_or_404(container_id, *auth)
    return {"text": await incus.show_log(c.name)}


@router.get("/{container_id}/config")
async def container_config(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    c = _container_or_404(container_id, *auth)
    return {"text": await incus.show_config(c.name)}


@router.get("/{container_id}/info")
async def container_info(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Live-Info aus incus: Status, CPU/Memory, IP."""
    c = _container_or_404(container_id, *auth)
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
