"""Communication-API — Channel-Liste."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.communication import all_channels

router = APIRouter(prefix="/api/communication", tags=["communication"])


@router.get("/channels")
async def list_channels(_=Depends(require_auth)) -> list[dict]:
    return [{"name": c.name, "label": c.label} for c in all_channels()]
