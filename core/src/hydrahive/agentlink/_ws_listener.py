"""AgentLink WebSocket-Listener: persistent connection mit Auto-Reconnect."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import websockets

from hydrahive.agentlink.protocol import WSEvent
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

OnEvent = Callable[[WSEvent], Awaitable[None]]

_listener_state: dict = {"task": None, "stop": None, "on_event": None, "last_error": None}

_connected: bool = False
_reconnect_attempts: int = 0
_last_connect_at: str | None = None


def _set_last_error(msg: str | None) -> None:
    _listener_state["last_error"] = msg


def last_error() -> str | None:
    return _listener_state.get("last_error")


def _set_connected(v: bool) -> None:
    global _connected, _last_connect_at
    if v and not _connected:
        from datetime import datetime, timezone
        _last_connect_at = datetime.now(timezone.utc).isoformat()
    _connected = v


def _bump_reconnect() -> None:
    global _reconnect_attempts
    _reconnect_attempts += 1


def is_connected() -> bool:
    return _connected


def reconnect_attempts() -> int:
    return _reconnect_attempts


def last_connect_at() -> str | None:
    return _last_connect_at


def start_listener(on_event: OnEvent) -> None:
    if _listener_state["task"] and not _listener_state["task"].done():
        return
    stop = asyncio.Event()
    _listener_state["stop"] = stop
    _listener_state["on_event"] = on_event
    _listener_state["task"] = asyncio.create_task(listen_loop(on_event, stop))


async def stop_listener() -> None:
    stop = _listener_state.get("stop")
    task = _listener_state.get("task")
    if stop:
        stop.set()
    if task:
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
    _listener_state["task"] = None
    _listener_state["stop"] = None


async def restart_listener() -> None:
    on_event = _listener_state.get("on_event")
    if not on_event:
        raise RuntimeError("listener_never_started")
    await stop_listener()
    _set_last_error(None)
    start_listener(on_event)


async def listen_loop(on_event: OnEvent, stop: asyncio.Event) -> None:
    if not settings.agentlink_ws_url:
        logger.info("AgentLink-Listener: keine ws_url → idle")
        await stop.wait()
        return

    ws_url = settings.agentlink_ws_url
    my_id = settings.agentlink_agent_id
    backoff = 1.0

    while not stop.is_set():
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("AgentLink-WS verbunden: %s", ws_url)
                _set_connected(True)
                backoff = 1.0
                await ws.send(json.dumps({"action": "subscribe", "channel": f"agent:{my_id}"}))

                async def reader():
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                        except json.JSONDecodeError:
                            logger.warning("AgentLink-WS: invalid JSON: %s", msg[:200])
                            continue
                        event = WSEvent(
                            type=data.get("type", ""),
                            state_id=data.get("state_id"),
                            to_agent=data.get("to_agent"),
                            from_agent=data.get("from_agent"),
                            timestamp=data.get("timestamp"),
                            raw=data,
                        )
                        try:
                            await on_event(event)
                        except Exception as e:
                            logger.exception("on_event Handler crashte: %s", e)

                reader_task = asyncio.create_task(reader())
                stop_task = asyncio.create_task(stop.wait())
                done, pending = await asyncio.wait(
                    [reader_task, stop_task], return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
                if stop.is_set():
                    return
        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
            _set_connected(False)
            _bump_reconnect()
            _set_last_error(f"{type(e).__name__}: {e}")
            logger.warning("AgentLink-WS-Disconnect: %s — Reconnect in %.1fs", e, backoff)
            try:
                await asyncio.wait_for(stop.wait(), timeout=backoff)
                return
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 60.0)
        except Exception as e:
            _set_connected(False)
            _bump_reconnect()
            _set_last_error(f"{type(e).__name__}: {e}")
            logger.exception("AgentLink-WS unerwarteter Fehler: %s", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
    _set_connected(False)
