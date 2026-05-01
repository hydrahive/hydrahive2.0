"""AgentLink-Client — REST für State-CRUD, WebSocket für Real-time-Push.

Persistent connection mit Auto-Reconnect (exponential backoff), Subscribe auf
agent:{my_id}-Channel, Future-Map für synchrones await:
  ask_agent registriert eine Future beim Send → Listener resolved sie wenn
  ein Antwort-State eintrifft.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import httpx
import websockets

from hydrahive.agentlink.protocol import State, WSEvent
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


_PENDING_FUTURES: dict[str, asyncio.Future] = {}


def register_pending(reply_to_state_id: str) -> asyncio.Future:
    """Erzeugt eine Future die auf den Antwort-State zu reply_to_state_id wartet."""
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    _PENDING_FUTURES[reply_to_state_id] = fut
    return fut


def cancel_pending(reply_to_state_id: str) -> None:
    fut = _PENDING_FUTURES.pop(reply_to_state_id, None)
    if fut and not fut.done():
        fut.cancel()


def resolve_pending(reply_to_state_id: str, response_state: State) -> bool:
    """Löst die wartende Future auf — returnt True wenn jemand wartete."""
    fut = _PENDING_FUTURES.pop(reply_to_state_id, None)
    if fut and not fut.done():
        fut.set_result(response_state)
        return True
    return False


async def post_state(state: State) -> State:
    """POST /states — synchrones REST."""
    url = settings.agentlink_url.rstrip("/") + "/states"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=state.model_dump(exclude_none=True, exclude={"extra"}))
        r.raise_for_status()
        return State.model_validate(r.json())


async def get_state(state_id: str) -> State | None:
    """GET /states/{id}."""
    url = settings.agentlink_url.rstrip("/") + f"/states/{state_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return State.model_validate(r.json())


async def list_specialists() -> list[str]:
    """Liefert alle bekannten Agent-IDs aus AgentLink. Nutzt /states-Liste mit
    distinct agent_id. Wenn AgentLink mal einen /agents-Endpoint hat, hier wechseln."""
    url = settings.agentlink_url.rstrip("/") + "/states"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params={"limit": 200})
        r.raise_for_status()
        data = r.json()
    ids = sorted({s.get("agent_id", "") for s in data if s.get("agent_id")})
    return [i for i in ids if i]


# WebSocket-Listener-Loop -----------------------------------------------------

OnEvent = Callable[[WSEvent], Awaitable[None]]

_listener_state: dict = {"task": None, "stop": None, "on_event": None, "last_error": None}


def _set_last_error(msg: str | None) -> None:
    _listener_state["last_error"] = msg


def last_error() -> str | None:
    return _listener_state.get("last_error")


def start_listener(on_event: OnEvent) -> None:
    """Startet den persistent WS-Listener als asyncio-Task. Idempotent — wenn
    bereits läuft, no-op."""
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
    """Stoppt den aktuellen Listener und startet einen neuen mit dem gleichen
    on_event-Handler. Bei Manual-Reconnect via UI."""
    on_event = _listener_state.get("on_event")
    if not on_event:
        raise RuntimeError("listener_never_started")
    await stop_listener()
    _set_last_error(None)
    start_listener(on_event)


async def listen_loop(on_event: OnEvent, stop: asyncio.Event) -> None:
    """Persistent WS-Listener: connect → subscribe agent:{my_id} → forward events.
    Reconnect mit exponential backoff bei Disconnect."""
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
                # Subscribe auf den eigenen Agent-Channel
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

                # Reader-Task + Stop-Wait parallel — wer zuerst kommt killt den anderen
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
            _set_last_error(f"{type(e).__name__}: {e}")
            logger.exception("AgentLink-WS unerwarteter Fehler: %s", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
    _set_connected(False)


# Connection-Health -----------------------------------------------------------

_connected: bool = False


def is_connected() -> bool:
    return _connected


def _set_connected(v: bool) -> None:
    global _connected
    _connected = v
