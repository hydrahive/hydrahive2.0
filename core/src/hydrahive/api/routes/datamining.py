from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import mirror, mirror_query

router = APIRouter(prefix="/api/datamining", tags=["datamining"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/events")
async def get_recent_events(_auth: Auth, limit: int = 100) -> dict:
    events = await mirror.recent_events(min(limit, 500))
    return {"active": mirror._pool is not None, "events": events}


@router.get("/search")
async def search_events(
    _auth: Auth,
    q: str = Query(default=""),
    event_type: str | None = None,
    agent_name: str | None = None,
    username: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    semantic: bool = False,
    limit: int = 20,
) -> dict:
    active = mirror._pool is not None
    if not active:
        return {"active": False, "results": [], "error": None}
    try:
        results = await mirror_query.search_events(
            q,
            event_type=event_type or None,
            agent_name=agent_name or None,
            username=username or None,
            from_date=from_date or None,
            to_date=to_date or None,
            semantic=semantic,
            limit=min(limit, 100),
        )
        return {"active": True, "results": results, "error": None}
    except ValueError as e:
        return {"active": True, "results": [], "error": str(e)}


@router.get("/sessions")
async def list_sessions(
    _auth: Auth,
    agent_name: str | None = None,
    username: str | None = None,
    limit: int = 50,
) -> dict:
    active = mirror._pool is not None
    if not active:
        return {"active": False, "sessions": []}
    sessions = await mirror_query.list_sessions(
        agent_name=agent_name or None,
        username=username or None,
        limit=min(limit, 200),
    )
    return {"active": True, "sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _auth: Auth) -> dict:
    detail = await mirror_query.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(404, "Session nicht gefunden")
    return detail


@router.get("/embed/status")
async def get_embed_status(_auth: Auth) -> dict:
    return await mirror_query.embed_status()


@router.post("/embed/reset")
async def reset_embeddings(_auth: Auth, event_type: str | None = None) -> dict:
    count = await mirror.reset_embeddings(event_type)
    return {"ok": True, "reset": count}


@router.post("/embed/backfill")
async def trigger_backfill(_auth: Auth) -> dict:
    from hydrahive.llm._config import load_config
    if mirror._pool is None:
        return {"ok": False, "reason": "Mirror nicht aktiv"}
    if mirror._backfill_running:
        return {"ok": False, "reason": "Backfill läuft bereits"}
    model = load_config().get("embed_model", "")
    if not model:
        return {"ok": False, "reason": "Kein Embedding-Modell konfiguriert"}
    import asyncio
    asyncio.get_running_loop().create_task(mirror._backfill_task(model))
    return {"ok": True, "model": model}
