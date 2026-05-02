"""Shared mutable state for the AgentLink WebSocket listener."""
from __future__ import annotations

_listener_state: dict = {"task": None, "stop": None, "on_event": None, "last_error": None}
_connected: bool = False
_reconnect_attempts: int = 0
_last_connect_at: str | None = None


def last_error() -> str | None:
    return _listener_state.get("last_error")


def is_connected() -> bool:
    return _connected


def reconnect_attempts() -> int:
    return _reconnect_attempts


def last_connect_at() -> str | None:
    return _last_connect_at


def _set_last_error(msg: str | None) -> None:
    _listener_state["last_error"] = msg


def _set_connected(v: bool) -> None:
    global _connected, _last_connect_at
    if v and not _connected:
        from datetime import datetime, timezone
        _last_connect_at = datetime.now(timezone.utc).isoformat()
    _connected = v


def _bump_reconnect() -> None:
    global _reconnect_attempts
    _reconnect_attempts += 1
