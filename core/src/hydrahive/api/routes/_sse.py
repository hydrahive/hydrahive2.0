from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any, AsyncIterator

_HEARTBEAT_S = 15  # Sekunden ohne Event → SSE-Keepalive-Comment senden


def encode_event(event: Any) -> str:
    """Encode a runner Event as an SSE frame.

    Falls back to dict() if asdict fails (non-dataclass), or just stringifies.
    """
    name = getattr(event, "type", "message")
    try:
        payload = asdict(event)
    except TypeError:
        payload = event if isinstance(event, dict) else {"value": str(event)}
    data = json.dumps(payload, ensure_ascii=False, default=_safe_default)
    return f"event: {name}\ndata: {data}\n\n"


def _safe_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


async def to_sse(events: AsyncIterator) -> AsyncIterator[str]:
    """Wrap an async iterator of events as an SSE byte-stream.

    Sendet alle _HEARTBEAT_S Sekunden einen SSE-Comment (: heartbeat) damit
    nginx/Browser die Verbindung nicht wegen Inaktivität schließen — wichtig
    während Compaction-Pausen (LLM-Summarize-Call kann 10-30s dauern).

    Benutzt asyncio.wait statt asyncio.wait_for, damit die innere Coroutine
    beim Timeout NICHT gecancelt wird. wait_for cancelt den __anext__()-Call,
    was den Async-Generator des Runners korrumpiert und alle folgenden Events
    verschluckt — sichtbar als „hängt nach erstem Heartbeat" bei langsamen
    Modellen (Opus + xhigh).
    """
    it = events.__aiter__()
    task: asyncio.Task | None = None
    try:
        while True:
            if task is None:
                task = asyncio.ensure_future(it.__anext__())
            done, _ = await asyncio.wait({task}, timeout=_HEARTBEAT_S)
            if not done:
                yield ": heartbeat\n\n"
                continue
            task = None
            try:
                yield encode_event(done.pop().result())
            except StopAsyncIteration:
                break
            except Exception as e:
                yield encode_event({"type": "error", "message": f"Stream-Fehler: {e}", "fatal": True})
                break
    finally:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, StopAsyncIteration, Exception):
                pass
