"""Signatur für AgentLink-States, die HydraHive selbst sendet (Task 3bd963b2, b1).

AgentLink hat keine Anmeldung, und nginx gibt /agentlink/api ins LAN (Dashboard).
Jeder im Netz könnte also einen State posten. Deshalb signiert HydraHive alles,
was es sendet, und nimmt Aufträge (``hh-target:``) und Antworten (``reply_to:``)
nur mit gültiger Signatur an.

- Schlüssel: aus ``settings.secret_key`` abgeleitet, nie der rohe JWT-Schlüssel.
- Signiert werden id, Absender, Ziel, reason (ohne Signatur), Aufgabe und
  Kontext. Jede Änderung, auch ein anderer State mit gleicher Signatur, fällt auf.
  Dateien in der Form, die AgentLink speichert (path/diff/lines/hash).
- Transport: letztes reason-Segment ``|hh-sig:v1:<hex>``. AgentLink speichert
  reason unverändert, fremde Felder verwirft es.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from hydrahive.agentlink.protocol import State

_SEGMENT = "|hh-sig:v1:"
_CONTEXT = b"hydrahive-agentlink-state-v1"


def _key() -> bytes:
    from hydrahive.settings import settings

    return hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()


def _split(reason: str) -> tuple[str, str | None]:
    """reason ohne Signatur + Signatur (oder None)."""
    head, sep, sig = reason.rpartition(_SEGMENT)
    if not sep or not sig or "|" in sig:
        return reason, None
    return head, sig


# Felder, die AgentLink pro Datei speichert (FileContext). Fehlende kommen als
# null zurück, alles andere verwirft AgentLink. Signiert wird genau diese Form,
# sonst passt die Signatur nach der Rundreise nicht mehr (Befund 01.10.2026).
_FILE_KEYS = ("path", "diff", "lines", "hash")


def _file_view(f: object) -> list:
    d = f if isinstance(f, dict) else {}
    out = []
    for k in _FILE_KEYS:
        v = d.get(k)
        out.append(list(v) if isinstance(v, (list, tuple)) else v)
    return out


def _payload(state: State, reason: str) -> bytes:
    files = state.context.files if state.context else []
    body = {
        "id": state.id,
        "agent_id": state.agent_id,
        "to_agent": state.handoff.to_agent if state.handoff else None,
        "reason": reason,
        "task": [state.task.type, state.task.description] if state.task else None,
        "files": [_file_view(f) for f in files],
        "errors": state.context.errors if state.context else [],
    }
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def _mac(state: State, reason: str) -> str:
    return hmac.new(_key(), _payload(state, reason), hashlib.sha256).hexdigest()


def sign(state: State) -> State:
    """Setzt eine id (falls leer) und hängt die Signatur an handoff.reason an."""
    if not state.id:
        state.id = str(uuid.uuid4())
    if state.handoff is None:
        return state
    reason, _old = _split(state.handoff.reason or "")
    state.handoff.reason = f"{reason}{_SEGMENT}{_mac(state, reason)}"
    return state


def is_valid(state: State) -> bool:
    """True nur bei vorhandener, passender Signatur."""
    if not state.id or state.handoff is None:
        return False
    reason, sig = _split(state.handoff.reason or "")
    if sig is None:
        return False
    return hmac.compare_digest(sig, _mac(state, reason))


def reply_target(reason: str | None) -> str | None:
    """State-ID aus ``reply_to:<id>``, ohne das Signatur-Segment.

    Regression 29.09.2026: Ohne Abtrennen landete ``|hh-sig:v1:…`` in der ID,
    und keine Antwort fand ihren wartenden ask_agent mehr.
    """
    head, _sig = _split(reason or "")
    if not head.startswith("reply_to:"):
        return None
    target = head.removeprefix("reply_to:").strip()
    return target or None
