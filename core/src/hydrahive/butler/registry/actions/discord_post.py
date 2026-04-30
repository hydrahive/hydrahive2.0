"""discord_post — Phase 2: Stub. Discord-Integration kommt später."""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.registry.actions._stub import stub_result
from hydrahive.butler.template import render


async def _execute(params: dict, event: TriggerEvent) -> ActionResult:
    rendered = {
        "channel_id": params.get("channel_id") or "",
        "message": render(params.get("message") or "", event),
    }
    return stub_result("discord_post", rendered)


register_action(ActionSpec(
    subtype="discord_post",
    label="Discord-Nachricht",
    description="Postet in einen Discord-Channel",
    params=[
        ParamSchema(key="channel_id", label="Channel-ID", kind="text", required=True),
        ParamSchema(key="message", label="Nachricht (Jinja2-Template)",
                    kind="textarea", required=True),
    ],
    execute=_execute,
))
