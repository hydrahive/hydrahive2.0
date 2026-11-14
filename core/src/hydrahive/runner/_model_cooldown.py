"""Kurze Sperre für gestörte Modelle (Spec agent-templates.md Kap. 8).

Fällt ein Modell mit einem Anbieter-/Kontoproblem aus (Limit, Quota, Überlast, Login), wird es für
`seconds` übersprungen, statt bei jedem Aufruf erneut dagegen zu laufen. Nur im Speicher des Prozesses;
nach einem Neustart ist alles wieder frei. Timeouts und leere Antworten sperren nicht.
"""
from __future__ import annotations

import time

DEFAULT_COOLDOWN_SECONDS = 300

_down_until: dict[str, float] = {}


def mark_down(model: str, seconds: float, *, now: float | None = None) -> None:
    if seconds <= 0 or not model:
        return
    _down_until[model] = (time.monotonic() if now is None else now) + seconds


def is_down(model: str, *, now: float | None = None) -> bool:
    until = _down_until.get(model)
    if until is None:
        return False
    if (time.monotonic() if now is None else now) >= until:
        _down_until.pop(model, None)
        return False
    return True


def available(models: list[str]) -> tuple[list[str], list[str]]:
    """(zu versuchende Modelle, übersprungene). Sind alle gesperrt, werden trotzdem alle versucht."""
    usable = [m for m in models if not is_down(m)]
    if not usable:
        return list(models), []
    return usable, [m for m in models if m not in usable]


def reset() -> None:
    _down_until.clear()
