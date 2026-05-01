from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.tailscale.control import logout, up
from hydrahive.tailscale.status import get_status

router = APIRouter(prefix="/api/tailscale", tags=["tailscale"])


class UpRequest(BaseModel):
    authkey: str


@router.get("/status")
async def tailscale_status(_=Depends(require_admin)) -> dict:
    return await get_status()


@router.post("/up")
async def tailscale_up(req: UpRequest, _=Depends(require_admin)) -> dict:
    try:
        await up(req.authkey)
        return await get_status()
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/logout")
async def tailscale_logout(_=Depends(require_admin)) -> dict:
    try:
        await logout()
        return await get_status()
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
