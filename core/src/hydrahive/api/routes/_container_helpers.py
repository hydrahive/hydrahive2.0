from __future__ import annotations

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded
from hydrahive.containers import db as cdb
from hydrahive.containers.models import MAX_CPU, MAX_RAM_MB, MIN_CPU, MIN_RAM_MB


class ContainerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    description: str | None = Field(default=None, max_length=500)
    image: str = Field(min_length=1, max_length=120)
    cpu: int | None = Field(default=None, ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int | None = Field(default=None, ge=MIN_RAM_MB, le=MAX_RAM_MB)
    network_mode: str = "bridged"


class ContainerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=63)
    description: str | None = Field(default=None, max_length=500)
    cpu: int | None = Field(default=None, ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int | None = Field(default=None, ge=MIN_RAM_MB, le=MAX_RAM_MB)
    clear_cpu: bool = False
    clear_ram: bool = False


def is_admin(role: str) -> bool:
    return role == "admin"


def container_or_404(container_id: str, owner: str, role: str):
    c = cdb.get(container_id)
    if not c:
        raise coded(status.HTTP_404_NOT_FOUND, "container_not_found")
    if c.owner != owner and not is_admin(role):
        raise coded(status.HTTP_403_FORBIDDEN, "container_no_access")
    return c
