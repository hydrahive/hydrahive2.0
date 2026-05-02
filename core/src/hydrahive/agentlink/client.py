"""AgentLink-Client — REST für State-CRUD, WebSocket für Real-time-Push.

Persistent connection mit Auto-Reconnect (exponential backoff), Subscribe auf
agent:{my_id}-Channel, Future-Map für synchrones await.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

import httpx

from hydrahive.agentlink._ws_listener import (
    OnEvent, is_connected, last_connect_at, last_error,
    listen_loop, reconnect_attempts,
    restart_listener, start_listener, stop_listener,
)
from hydrahive.agentlink.protocol import State, WSEvent
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# Re-export so callers don't need to know about the split
__all__ = [
    "register_pending", "cancel_pending", "resolve_pending",
    "post_state", "get_state", "list_specialists", "list_specialists_with_meta",
    "start_listener", "stop_listener", "restart_listener", "listen_loop",
    "is_connected", "last_error", "reconnect_attempts", "last_connect_at",
    "OnEvent",
]

_PENDING_FUTURES: dict[str, asyncio.Future] = {}


def register_pending(reply_to_state_id: str) -> asyncio.Future:
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    _PENDING_FUTURES[reply_to_state_id] = fut
    return fut


def cancel_pending(reply_to_state_id: str) -> None:
    fut = _PENDING_FUTURES.pop(reply_to_state_id, None)
    if fut and not fut.done():
        fut.cancel()


def resolve_pending(reply_to_state_id: str, response_state: State) -> bool:
    fut = _PENDING_FUTURES.pop(reply_to_state_id, None)
    if fut and not fut.done():
        fut.set_result(response_state)
        return True
    return False


def pending_handoffs_count() -> int:
    return len(_PENDING_FUTURES)


async def post_state(state: State) -> State:
    url = settings.agentlink_url.rstrip("/") + "/states"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=state.model_dump(exclude_none=True, exclude={"extra"}))
        r.raise_for_status()
        return State.model_validate(r.json())


async def get_state(state_id: str) -> State | None:
    url = settings.agentlink_url.rstrip("/") + f"/states/{state_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return State.model_validate(r.json())


async def list_specialists() -> list[str]:
    metas = await list_specialists_with_meta()
    return [m["agent_id"] for m in metas]


async def list_specialists_with_meta() -> list[dict]:
    url = settings.agentlink_url.rstrip("/") + "/states"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params={"limit": 200})
        r.raise_for_status()
        data = r.json()
    by_agent: dict[str, dict] = {}
    for s in data:
        aid = s.get("agent_id") or ""
        if not aid:
            continue
        ts = s.get("created_at") or ""
        cur = by_agent.setdefault(aid, {"agent_id": aid, "last_seen": "", "states": 0})
        cur["states"] += 1
        if ts > cur["last_seen"]:
            cur["last_seen"] = ts
    return sorted(by_agent.values(), key=lambda x: x["last_seen"], reverse=True)
