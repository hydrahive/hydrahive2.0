from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, AsyncIterator


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
    """Wrap an async iterator of events as an SSE byte-stream."""
    try:
        async for ev in events:
            yield encode_event(ev)
    except Exception as e:
        yield encode_event({"type": "error", "message": f"Stream-Fehler: {e}", "fatal": True})
