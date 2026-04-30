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
    description="HTTP-POST an /api/webhooks/butler/<hook_id> (Pro-Hook-Secret)",
    params=[
        ParamSchema(
            key="hook_id", label="Hook-ID", kind="text",
            placeholder="my-hook", required=True,
        ),
    ],
    matches=_matches,
))
