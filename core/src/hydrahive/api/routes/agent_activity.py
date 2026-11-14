"""SSE-Feed laufender Agenten für die Pixel-Leiste und das Agenten-Büro (nur eigene Agenten)."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.routes._trace_extras import github_link, result_summary
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.runner import activity

router = APIRouter(prefix="/api/agents/activity", tags=["agents"])


@router.get("/stream")
async def stream_activity(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> StreamingResponse:
    username, _role = auth
    queue = activity.broadcaster.subscribe()

    async def _events():
        try:
            yield f"data: {json.dumps(activity.snapshot(username))}\n\n"
            while True:
                try:
                    await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {json.dumps(activity.snapshot(username))}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            activity.broadcaster.unsubscribe(queue)

    return StreamingResponse(
        _events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/{session_id}/trace")
async def get_trace(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Tool-Call-Verlauf einer Session für den Live-Drawer im Agenten-Büro (Spec agent-office.md §2).

    Neueste zuerst. Nur der Owner der Session sieht sie — Fremdzugriff und unbekannte Session liefern
    beide 404 (kein Unterschied nach außen, damit man Session-IDs nicht erraten/bestätigen kann).
    """
    username, _role = auth
    session = sessions_db.get(session_id)
    if session is None or session.user_id != username:
        raise HTTPException(404, "Session nicht gefunden")
    calls = list(reversed(tools_db.list_for_session(session_id)))
    return {
        "session_id": session_id,
        "calls": [
            {
                "id": c.id,
                "tool_name": c.tool_name,
                "status": c.status,
                "duration_ms": c.duration_ms,
                "created_at": c.created_at,
                "iteration": c.iteration,
                "result_summary": result_summary(c.result),
                "github_link": github_link(c.result),
            }
            for c in calls
        ],
    }
