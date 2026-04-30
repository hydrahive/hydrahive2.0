from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ParamSchema, TriggerSpec, register_trigger,
)


def _matches(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "message":
        return False
    want = (params.get("channel") or "all").lower()
    if want == "all":
        return True
    return (event.channel or "").lower() == want


register_trigger(TriggerSpec(
    subtype="message_received",
    label="Nachricht eingegangen",
    description="Eingehende Nachricht über einen Channel (WhatsApp / Telegram / …)",
    params=[
        ParamSchema(
            key="channel", label="Channel", kind="select",
            options=["all", "whatsapp", "telegram", "discord", "matrix"],
            default="all",
        ),
    ],
    matches=_matches,
))
