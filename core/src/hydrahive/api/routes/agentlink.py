"""AgentLink-Status für die System-Page."""
from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from hydrahive.agentlink import is_connected, list_specialists
from hydrahive.api.middleware.auth import require_auth
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
        "url": settings.agentlink_url,
        "ws_url": settings.agentlink_ws_url,
        "agent_id": settings.agentlink_agent_id,
        "handoff_timeout_s": settings.agentlink_handoff_timeout,
        "known_agents": specs,
    }
