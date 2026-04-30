"""ignore — Bypass für default-Verhalten (z.B. nicht zum Master-Agent weiterleiten)."""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, register_action,
)


async def _execute(_: dict, __: TriggerEvent) -> ActionResult:
    return ActionResult(ok=True, detail="ignored")


register_action(ActionSpec(
    subtype="ignore",
    label="Ignorieren",
    description="Stoppt den Flow ohne Side-Effects (Bypass des Default-Verhaltens)",
    params=[],
    execute=_execute,
))
