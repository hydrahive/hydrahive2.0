from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.tailscale.admin import (
    create_invite, public_config, save_admin_config, validate_api_key,
)
from hydrahive.tailscale.control import logout, up
from hydrahive.tailscale.install import install_tailscale
from hydrahive.tailscale.status import get_status

router = APIRouter(prefix="/api/tailscale", tags=["tailscale"])


class UpRequest(BaseModel):
    authkey: str


class AdminConfigRequest(BaseModel):
    api_key: str
    tailnet: str = "-"


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


@router.post("/install")
async def tailscale_install(_=Depends(require_admin)) -> dict:
    """Installiert Tailscale-Binary via Installer-Modul (idempotent).

    Returnt {ok, rc, output, status} — Frontend kann output bei rc != 0 anzeigen.
    """
    result = await install_tailscale()
    result["status"] = await get_status()
    return result


@router.get("/admin-config")
async def tailscale_admin_config_get(_=Depends(require_admin)) -> dict:
    """Returnt {configured, tailnet}. Niemals den api_key — auch nicht maskiert."""
    return public_config()


@router.put("/admin-config")
async def tailscale_admin_config_put(req: AdminConfigRequest, _=Depends(require_admin)) -> dict:
    """Validiert api_key gegen Tailscale-API (probt /devices) und speichert mode 0600."""
    ok, err = await validate_api_key(req.api_key, req.tailnet)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "tailscale_admin_key_invalid", "params": {"reason": err}},
        )
    save_admin_config(req.api_key, req.tailnet)
    return public_config()


@router.post("/invite")
async def tailscale_invite(_=Depends(require_admin)) -> dict:
    """Generiert einen 24h-Single-Use-Pre-Auth-Key über die Tailscale-API."""
    try:
        return await create_invite()
    except RuntimeError as e:
        code = str(e)
        http_status = (
            status.HTTP_400_BAD_REQUEST if code == "tailscale_admin_not_configured"
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=http_status, detail={"code": code, "params": {}})
