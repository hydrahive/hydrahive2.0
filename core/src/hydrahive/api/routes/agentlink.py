"""AgentLink-Status + manueller Reconnect-Trigger."""
from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from hydrahive.agentlink import is_connected, last_error, list_specialists, restart_listener
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/agentlink", tags=["agentlink"])


@router.get("/status")
async def status(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    if not settings.agentlink_url:
        return {"configured": False, "connected": False}

    backend_reachable = False
    specs: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(settings.agentlink_url.rstrip("/") + "/docs")
            backend_reachable = r.status_code == 200
        if backend_reachable:
            specs = await list_specialists()
    except Exception:
        pass

    return {
        "configured": True,
        "connected": is_connected() or backend_reachable,
        "ws_connected": is_connected(),
        "backend_reachable": backend_reachable,
        "last_error": last_error(),
        "url": settings.agentlink_url,
        "ws_url": settings.agentlink_ws_url,
        "agent_id": settings.agentlink_agent_id,
        "handoff_timeout_s": settings.agentlink_handoff_timeout,
        "known_agents": specs,
        "dashboard_url": settings.agentlink_dashboard_url,
    }


@router.post("/reconnect", dependencies=[Depends(require_admin)])
async def reconnect() -> dict:
    if not settings.agentlink_url:
        raise coded(400, "agentlink_not_configured")
    try:
        await restart_listener()
    except RuntimeError as e:
        raise coded(409, "agentlink_listener_never_started" if str(e) == "listener_never_started" else "agentlink_failed", detail=str(e))
    return {"ok": True}
