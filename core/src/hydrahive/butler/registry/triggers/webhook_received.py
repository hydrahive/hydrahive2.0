from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ParamSchema, TriggerSpec, register_trigger,
)


def _matches(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "webhook":
        return False
    want_hook = params.get("hook_id") or ""
    if not want_hook:
        return True
    return (event.channel or "") == want_hook


register_trigger(TriggerSpec(
    subtype="webhook_received",
    label="Webhook eingegangen",
    description="Feuert bei einem Projekt-Webhook (POST /api/butler/webhooks/project/{id}). "
                "Hook-ID matcht den Event-Channel (z.B. 'project:<id>'); leer = jeder Webhook.",
    params=[
        ParamSchema(
            key="hook_id", label="Hook-ID", kind="text",
            placeholder="my-hook", required=True,
        ),
    ],
    matches=_matches,
))
