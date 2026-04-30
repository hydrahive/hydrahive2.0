"""reply_fixed — feste Antwort über den Channel zurück.

Action selbst sendet NICHT — sie liefert nur den gerenderten Text als
`reply_text`. Der Channel-Router (handle_incoming) sendet dann.
"""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.template import render


async def _execute(params: dict, event: TriggerEvent) -> ActionResult:
    text = render(params.get("text") or "", event)
    return ActionResult(
        ok=True, detail="reply_fixed",
        reply_text=text, stop_default=True,
    )


register_action(ActionSpec(
    subtype="reply_fixed",
    label="Feste Antwort senden",
    description="Schickt einen festen Text als Antwort über den Channel zurück",
    params=[
        ParamSchema(
            key="text", label="Antwort", kind="textarea", required=True,
            placeholder="Bin gerade nicht erreichbar.",
        ),
    ],
    execute=_execute,
))
