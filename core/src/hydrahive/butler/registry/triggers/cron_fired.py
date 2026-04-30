from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ParamSchema, TriggerSpec, register_trigger,
)


def _matches(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "cron":
        return False
    want_id = (params.get("schedule_id") or "").strip()
    if want_id:
        return (event.payload.get("schedule_id") or "") == want_id
    return True


register_trigger(TriggerSpec(
    subtype="cron_fired",
    label="Zeitplan",
    description="Wird zeitgesteuert ausgelöst (z.B. täglich um 8 Uhr)",
    params=[
        ParamSchema(
            key="schedule_id", label="Schedule-ID", kind="text",
            placeholder="daily-morning",
        ),
        ParamSchema(
            key="cron", label="Cron-Expression", kind="text",
            placeholder="0 8 * * *",
        ),
    ],
    matches=_matches,
))
