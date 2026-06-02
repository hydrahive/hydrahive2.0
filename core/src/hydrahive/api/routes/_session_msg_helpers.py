from __future__ import annotations

import time

from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.api._session_broadcast import broadcaster
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._files import process_upload
from hydrahive.api.routes._sse import to_sse
from hydrahive.runner import run as runner_run
from hydrahive.runner.concurrency import SessionAlreadyRunning, is_running, session_run_guard

# Live-Sync v1: max ein Aktivitäts-Ping pro Intervall während eines Laufs.
_PING_INTERVAL_S = 0.5


async def build_user_content(agent_id: str, text: str, files: list[UploadFile]) -> str | list:
    if not files:
        return text
    agent = agent_config.get(agent_id)
    workspace = ensure_workspace(agent) if agent else None
    blocks: list[dict] = []
    for f in files:
        blocks.extend(await process_upload(f, workspace))
    blocks.append({"type": "text", "text": text})
    return blocks


def sse_run_response(events) -> StreamingResponse:
    return StreamingResponse(
        to_sse(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def sse_run_with_guard(session_id: str, user_content, *, extra_system: str | None = None) -> StreamingResponse:
    """SSE-Response für runner_run MIT Session-Concurrency-Guard.

    409 wenn für die Session bereits ein Run läuft. Verhindert dass
    bei abgerissenem SSE-Stream (Browser-Refresh, Modell-Switch, Network-Hiccup)
    ein zweiter Run parallel angestoßen wird — siehe runner.concurrency
    für den Hintergrund.
    """
    if is_running(session_id):
        raise coded(status.HTTP_409_CONFLICT, "session_already_running")

    async def _guarded_stream():
        # Live-Sync v1: leichte Pings an alle Geräte derselben Session, damit ein
        # passives Tab/Tablet bei Lauf-Fortschritt nachlädt. Der Sender-Stream
        # (yield ev) bleibt davon unberührt.
        last_ping = 0.0
        try:
            async with session_run_guard(session_id):
                broadcaster.broadcast(session_id, '{"t":"start"}')
                if extra_system is not None:
                    gen = runner_run(session_id, user_content, extra_system=extra_system)
                else:
                    gen = runner_run(session_id, user_content)
                async for ev in gen:
                    yield ev
                    now = time.monotonic()
                    if now - last_ping >= _PING_INTERVAL_S:
                        last_ping = now
                        broadcaster.broadcast(session_id, '{"t":"activity"}')
        except SessionAlreadyRunning:
            return  # lost the race between is_running() check and acquire
        finally:
            broadcaster.broadcast(session_id, '{"t":"done"}')

    return sse_run_response(_guarded_stream())
