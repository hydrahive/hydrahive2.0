"""Helper für SMB-Mount-Routes — Serialisierung + Request-Bodies.

mount_dict gibt bewusst NIE Credential-Werte/Passwörter aus — nur den
Credential-Namen als Referenz.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from hydrahive.smbmounts.models import SmbMount


def mount_dict(m: SmbMount) -> dict:
    return {
        "id": m.mount_id,
        "name": m.name,
        "host": m.host,
        "share": m.share,
        "subpath": m.subpath,
        "credential": m.credential,
        "read_only": m.read_only,
        "options": m.options,
        "project_id": m.project_id,
        "mount_state": m.mount_state,
        "last_error_code": m.last_error_code,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


class CreateMountRequest(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    host: str = Field(min_length=1, max_length=253)
    share: str = Field(min_length=1, max_length=80)
    subpath: str | None = Field(default=None, max_length=255)
    credential: str | None = None
    read_only: bool = False
    options: str | None = None


class UpdateMountRequest(BaseModel):
    host: str | None = Field(default=None, max_length=253)
    share: str | None = Field(default=None, max_length=80)
    subpath: str | None = Field(default=None, max_length=255)
    credential: str | None = None
    read_only: bool | None = None
    options: str | None = None


class AssignMountRequest(BaseModel):
    id: str
