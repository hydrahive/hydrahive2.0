"""Admin-API: externer Server fürs Archiv (docs/specs/archiv-system.md, Etappe 3).

Einstellungen (ohne Passwort in der Antwort), Verbindungstest, aktiv schalten (nur nach Test),
Abgleich. Alles nur für Admins.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, StrictBool

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.archive import remote_config, remote_sync
from hydrahive.archive.remote_smb import RemoteError

router = APIRouter(prefix="/api/admin/archive/remote", tags=["admin"], dependencies=[Depends(require_admin)])


class RemoteSettings(BaseModel):
    host: str
    share: str
    subdir: str = ""
    user: str = ""
    password: str = ""


class RemoteActive(BaseModel):
    active: StrictBool


@router.get("")
def remote_get() -> dict:
    return remote_config.public()


@router.put("")
def remote_put(req: RemoteSettings) -> dict:
    try:
        return remote_config.save(req.model_dump())
    except remote_config.RemoteConfigError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, field=e.field)


@router.post("/test")
async def remote_test() -> dict:
    return await asyncio.to_thread(remote_config.test)


@router.post("/active")
async def remote_active(req: RemoteActive) -> dict:
    try:
        result = remote_config.set_active(req.active)
    except remote_config.RemoteConfigError as e:
        raise coded(status.HTTP_409_CONFLICT, e.code)
    if req.active:
        await asyncio.to_thread(remote_sync.on_start)        # gleich alles nachholen, was fehlt
    return result


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def remote_sync_now() -> dict:
    if not remote_config.is_active():
        raise coded(status.HTTP_409_CONFLICT, "archive_remote_inactive")
    try:
        return {"queued": await asyncio.to_thread(remote_sync.sync)}
    except RemoteError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, "archive_remote_failed", reason=e.code)


def status_block() -> dict:
    """Für GET /api/admin/archive/status: Einstellungen + Reihe + gezählte Pakete."""
    from hydrahive.archive import catalog
    counts = {"on_server": 0, "local_only": 0}
    for e in catalog.list_entries():
        state = (e.get("remote") or {}).get("state")
        counts["on_server" if state == "verified" else "local_only"] += 1
    return {**remote_config.public(), **remote_sync.summary(), **counts}
