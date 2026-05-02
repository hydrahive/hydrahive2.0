"""Container CRUD routes (list / create / get / update / delete)."""
from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._container_helpers import (
    ContainerCreate, ContainerUpdate, container_or_404, is_admin,
)
from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus
from hydrahive.containers import lifecycle
from hydrahive.containers.models import NAME_RE, QUICK_IMAGES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/containers", tags=["containers"])


@router.get("")
def list_containers(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, role = auth
    cs = cdb.list_(owner=None if is_admin(role) else user)
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
    return asdict(container_or_404(container_id, *auth))


@router.patch("/{container_id}")
def update_container(
    container_id: str,
    req: ContainerUpdate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    c = container_or_404(container_id, *auth)
    if c.actual_state not in ("stopped", "created", "error"):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_must_be_stopped",
                    state=c.actual_state)
    if req.name and req.name != c.name and not re.match(NAME_RE, req.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_name_invalid", name=req.name)
    if req.name and req.name != c.name and cdb.name_taken(req.name, exclude_id=container_id):
        raise coded(status.HTTP_409_CONFLICT, "container_name_taken", name=req.name)
    cdb.update_container_config(
        container_id,
        name=req.name,
        description=req.description if req.description is not None else ...,
        cpu=None if req.clear_cpu else (req.cpu if req.cpu is not None else ...),
        ram_mb=None if req.clear_ram else (req.ram_mb if req.ram_mb is not None else ...),
    )
    return asdict(cdb.get(container_id))  # type: ignore[arg-type]


@router.delete("/{container_id}", status_code=204)
async def delete_container(
    container_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    container_or_404(container_id, *auth)
    await lifecycle.delete(container_id)
