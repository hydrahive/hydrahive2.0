"""AgentLink-Integration für HydraHive2.

Verbindet zum existierenden AgentLink-Service (siehe github.com/hydrahive/hydralink)
für Agent-zu-Agent State-Transfer. WebSocket-basiert für Real-time-Handoff-Empfang.
"""
from hydrahive.agentlink.client import (
    cancel_pending,
    get_state,
    is_connected,
    last_error,
    list_specialists,
    listen_loop,
    post_state,
    register_pending,
    resolve_pending,
    restart_listener,
    start_listener,
    stop_listener,
)
from hydrahive.agentlink.protocol import (
    ContextBlock,
    Handoff,
    State,
    TaskBlock,
    WorkingMemory,
    WSEvent,
)

__all__ = [
    "cancel_pending", "get_state", "is_connected", "last_error",
    "list_specialists", "listen_loop", "post_state", "register_pending",
    "resolve_pending", "restart_listener", "start_listener", "stop_listener",
    "ContextBlock", "Handoff", "State", "TaskBlock", "WorkingMemory", "WSEvent",
]
