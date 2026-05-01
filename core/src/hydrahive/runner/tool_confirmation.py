"""Pending-Store für Tool-Bestätigungen vor Ausführung.

Wenn `require_tool_confirm` am Agent gesetzt ist, wartet der Runner auf eine
User-Entscheidung bevor das Tool läuft. Frontend bekommt SSE-Event
`tool_confirm_required`, antwortet via POST /sessions/{sid}/tool-confirm/{cid}.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300.0  # 5 Minuten — danach automatisch deny

Decision = Literal["approve", "deny"]


_pending: dict[str, asyncio.Future[Decision]] = {}


def register(call_id: str) -> asyncio.Future[Decision]:
    fut: asyncio.Future[Decision] = asyncio.get_event_loop().create_future()
    _pending[call_id] = fut
    return fut


def resolve(call_id: str, decision: Decision) -> bool:
    fut = _pending.pop(call_id, None)
    if fut is None or fut.done():
        return False
    fut.set_result(decision)
    return True


async def wait(call_id: str, timeout: float = DEFAULT_TIMEOUT) -> Decision:
    fut = _pending.get(call_id)
    if fut is None:
        return "deny"
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        _pending.pop(call_id, None)
        logger.warning("tool_confirm timeout für call_id=%s — auto-deny", call_id)
        return "deny"


def cancel(call_id: str) -> None:
    fut = _pending.pop(call_id, None)
    if fut and not fut.done():
        fut.cancel()
