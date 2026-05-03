from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import mirror

router = APIRouter(prefix="/api/datamining", tags=["datamining"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/events")
async def get_recent_events(_auth: Auth, limit: int = 100) -> dict:
    events = await mirror.recent_events(min(limit, 500))
    return {
        "active": mirror._pool is not None,
        "events": events,
    }
