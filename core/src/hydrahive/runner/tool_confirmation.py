"""Pending-Store für Tool-Bestätigungen vor Ausführung.

Wenn eine Bestätigung nötig ist (`require_tool_confirm` am Agenten, Harakiri-Schutz,
Discord-Löschen …), wartet der Runner auf eine Entscheidung, bevor das Tool läuft.
Frontend bekommt das SSE-Event `tool_confirm_required` und antwortet per
POST /sessions/{sid}/tool-confirm/{cid}.

Warten statt Ablehnen (docs/specs/harakiri-confirm-noise.md, Punkt 3): `wait`
ohne Zeitlimit wartet, bis jemand entscheidet oder der Lauf gestoppt wird. Ein
abgelaufenes Limit ist „timeout“, keine Ablehnung durch den Benutzer. Die
offene Bestätigung bleibt je Session abfragbar (`pending_for`), damit die
Oberfläche das Banner nach dem Neuladen wieder zeigt.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

Decision = Literal["approve", "deny"]
Outcome = Literal["approve", "deny", "timeout"]


@dataclass
class _Pending:
    future: asyncio.Future[Decision]
    session_id: str | None = None
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    reason: str | None = None


_pending: dict[str, _Pending] = {}


def register(
    call_id: str, *, session_id: str | None = None, tool_name: str = "",
    arguments: dict | None = None, reason: str | None = None,
) -> asyncio.Future[Decision]:
    fut: asyncio.Future[Decision] = asyncio.get_running_loop().create_future()
    _pending[call_id] = _Pending(fut, session_id, tool_name, dict(arguments or {}), reason)
    return fut


def resolve(call_id: str, decision: Decision) -> bool:
    p = _pending.pop(call_id, None)
    if p is None or p.future.done():
        return False
    p.future.set_result(decision)
    return True


async def wait(call_id: str, timeout: float | None) -> Outcome:
    """Wartet auf die Entscheidung. `timeout=None` = ohne Limit. Wird der
    wartende Lauf abgebrochen (Stopp), verschwindet die offene Bestätigung."""
    p = _pending.get(call_id)
    if p is None:
        return "deny"
    try:
        return await asyncio.wait_for(p.future, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("tool_confirm: keine Antwort für call_id=%s nach %ss", call_id, timeout)
        return "timeout"
    finally:
        cancel(call_id)


def pending_for(session_id: str) -> dict | None:
    """Offene Bestätigung einer Session (für run-status), sonst None."""
    for call_id, p in _pending.items():
        if p.session_id == session_id and not p.future.done():
            return {"call_id": call_id, "tool_name": p.tool_name,
                    "arguments": p.arguments, "reason": p.reason}
    return None


def cancel(call_id: str) -> None:
    p = _pending.pop(call_id, None)
    if p and not p.future.done():
        p.future.cancel()
