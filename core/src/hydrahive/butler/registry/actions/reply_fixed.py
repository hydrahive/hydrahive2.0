"""reply_fixed — feste Antwort zurück über den Channel.
Phase 2: Stub. Phase 4 ruft den Channel-Adapter."""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.registry.actions._stub import stub_result
from hydrahive.butler.template import render


async def _execute(params: dict, event: TriggerEvent) -> ActionResult:
    rendered = {"text": render(params.get("text") or "", event)}
    return stub_result("reply_fixed", rendered)


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
