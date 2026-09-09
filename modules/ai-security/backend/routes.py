"""Authentifizierte API für den AI-Infra-Guard-MVP."""
from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.settings import settings

from .aig_client import AigClient, AigError
from .config import ConfigError, configured_targets, validate_target
from . import service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-security"])
Auth = Annotated[tuple[str, str], Depends(require_auth)]


class ScanIn(BaseModel):
    scan_type: Literal["infra"] = "infra"
    target_url: str = Field(min_length=1, max_length=300)


def _aig_error(exc: AigError) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.code)


@router.get("/health")
async def health(_: Auth) -> dict[str, Any]:
    if not settings.ai_security_enabled:
        return {"configured": False, "reachable": False, "error": "disabled"}
    try:
        configured = bool(settings.ai_security_aig_url)
        if not configured:
            return {"configured": False, "reachable": False, "error": "not_configured"}
        await AigClient().health()
        return {"configured": True, "reachable": True, "error": None}
    except AigError as exc:
        return {"configured": True, "reachable": False, "error": exc.code}


@router.get("/targets")
def targets(_: Auth) -> list[str]:
    try:
        return [target.origin for target in configured_targets()]
    except ConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="invalid_configuration") from exc


@router.get("/scans")
def list_scans(
    auth: Auth,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict[str, Any]]:
    return service.list_scans(auth[0], limit=limit)


@router.post("/scans", status_code=status.HTTP_202_ACCEPTED)
async def create_scan(body: ScanIn, auth: Auth) -> dict[str, Any]:
    if not settings.ai_security_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="disabled")
    try:
        target_url = validate_target(body.target_url)
    except ConfigError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    scan = service.create_scan(auth[0], target_url)
    try:
        session_id = await AigClient().create_infra_scan(target_url)
    except AigError as exc:
        service.mark_failed(scan["id"], exc.code)
        raise _aig_error(exc) from exc
    except Exception:
        logger.exception("AI-Security-Scan %s: unerwarteter Upstream-Fehler", scan["id"])
        service.mark_failed(scan["id"], "aig_internal_error")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="aig_internal_error",
        )
    service.update_session(scan["id"], session_id)
    return service.get_scan(auth[0], scan["id"]) or scan


@router.get("/scans/{scan_id}")
def get_scan(scan_id: str, auth: Auth) -> dict[str, Any]:
    scan = service.get_scan(auth[0], scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return scan
