"""Container CRUD routes (list / create / get / update / delete)."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware import users
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._container_helpers import (
    ContainerCreate,
    ContainerUpdate,
    container_or_404,
    is_admin,
)
from hydrahive.containers import db as cdb
from hydrahive.containers import execution
from hydrahive.containers import incus_client as incus
from hydrahive.containers import remote
from hydrahive.containers.models import IMAGE_RE, NAME_RE, QUICK_IMAGES

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


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_container(
    body: ContainerCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, role = auth
    if body.node_id != "local" and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "container_remote_placement_forbidden")
    if not re.match(NAME_RE, body.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_name_invalid")
    if body.network_mode not in ("bridged", "isolated"):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_network_mode_invalid")
    # Image gegen Allowlist prüfen, BEVOR der images:-Präfix gesetzt wird (#185)
    image = body.image.strip()
    if not re.match(IMAGE_RE, image):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_image_invalid")
    if ":" not in image:
        image = f"images:{image}"
    if cdb.name_taken(body.name):
        raise coded(status.HTTP_409_CONFLICT, "container_name_taken")
    if body.node_id == "local" and not incus.is_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "incus_missing")

    c = cdb.create(
        owner=user,
        name=body.name,
        description=body.description,
        image=image,
        cpu=body.cpu,
        ram_mb=body.ram_mb,
        network_mode=body.network_mode,
        node_id=body.node_id,
    )
    actor = users.get_by_username(user)
    try:
        await execution.create_and_start(
            c.container_id,
            actor=actor["user_id"] if actor is not None else user,
        )
    except incus.IncusError as e:
        cdb.delete(c.container_id)
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, e.code, **e.params)
    except remote.RemoteContainerError as e:
        cdb.delete(c.container_id)
        raise coded(status.HTTP_409_CONFLICT, "container_remote_unavailable", reason=str(e))
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
    if c.node_id != "local":
        raise coded(status.HTTP_400_BAD_REQUEST, "container_remote_config_not_supported")
    if c.actual_state not in ("stopped", "created", "error"):
        raise coded(status.HTTP_400_BAD_REQUEST, "container_must_be_stopped", state=c.actual_state)
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
    actor = users.get_by_username(auth[0])
    try:
        await execution.delete(container_id, actor=actor["user_id"] if actor is not None else auth[0])
    except remote.RemoteContainerError as exc:
        raise coded(status.HTTP_409_CONFLICT, "container_remote_unavailable", reason=str(exc))
