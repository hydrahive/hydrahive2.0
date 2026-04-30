"""ignore + queue — Bypass des Default-Verhaltens (kein Master-Agent-Aufruf).

Beide Actions stoppen den Default — bei `ignore` passiert sonst nichts,
bei `queue` wäre Phase-X eine Queue-Anbindung. Aktuell verhalten sie
sich identisch.
"""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, register_action,
)


async def _execute(_: dict, __: TriggerEvent) -> ActionResult:
    return ActionResult(ok=True, detail="ignored", stop_default=True)


register_action(ActionSpec(
    subtype="ignore",
    label="Ignorieren",
    description="Stoppt den Flow ohne Side-Effects (Bypass des Default-Verhaltens)",
    params=[], execute=_execute,
))

register_action(ActionSpec(
    subtype="queue",
    label="In Queue legen",
    description="Aktuell wie ignore — Queue-Anbindung kommt später",
    params=[], execute=_execute,
))
