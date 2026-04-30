from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ParamSchema, TriggerSpec, register_trigger,
)


def _matches(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "email":
        return False
    folder = (params.get("folder") or "").strip()
    if folder:
        if (event.payload.get("folder") or "INBOX").lower() != folder.lower():
            return False
    return True


register_trigger(TriggerSpec(
    subtype="email_received",
    label="Email eingegangen",
    description="Neue Email in einem IMAP-Ordner",
    params=[
        ParamSchema(
            key="folder", label="Ordner", kind="text",
            placeholder="INBOX", default="INBOX",
        ),
    ],
    matches=_matches,
))
