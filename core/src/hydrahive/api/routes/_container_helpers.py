from __future__ import annotations

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded
from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus
from hydrahive.containers import lifecycle
from hydrahive.containers.models import MAX_CPU, MAX_RAM_MB, MIN_CPU, MIN_RAM_MB, Container


class ContainerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    description: str | None = Field(default=None, max_length=500)
    image: str = Field(min_length=1, max_length=120)
    cpu: int | None = Field(default=None, ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int | None = Field(default=None, ge=MIN_RAM_MB, le=MAX_RAM_MB)
    network_mode: str = "bridged"
    node_id: str = Field(default="local", min_length=1, max_length=128)


class ContainerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=63)
    description: str | None = Field(default=None, max_length=500)
    cpu: int | None = Field(default=None, ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int | None = Field(default=None, ge=MIN_RAM_MB, le=MAX_RAM_MB)
    clear_cpu: bool = False
    clear_ram: bool = False


def is_admin(role: str) -> bool:
    return role == "admin"


def ensure_local_container(container: Container) -> None:
    try:
        lifecycle.ensure_local(container)
    except incus.IncusError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code, **exc.params)


def container_or_404(container_id: str, owner: str, role: str) -> Container:
    c = cdb.get(container_id)
    if not c:
        raise coded(status.HTTP_404_NOT_FOUND, "container_not_found")
    if c.owner != owner and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "container_no_access")
    return c
