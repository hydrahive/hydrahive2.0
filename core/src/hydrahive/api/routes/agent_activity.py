"""SSE-Feed laufender Agenten für die Pixel-Leiste (nur eigene Agenten)."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_auth
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
