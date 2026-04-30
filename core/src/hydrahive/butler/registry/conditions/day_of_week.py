from datetime import datetime

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ConditionSpec, ParamSchema, register_condition,
)

_DAYS = ["mo", "di", "mi", "do", "fr", "sa", "so"]


def _evaluate(params: dict, _: TriggerEvent) -> bool:
    days = params.get("days") or []
    if not isinstance(days, list):
        return False
    today = _DAYS[datetime.now().weekday()]
    return today in [str(d).lower() for d in days]


register_condition(ConditionSpec(
    subtype="day_of_week",
    label="Wochentag",
    description="Heutiger Wochentag in der Liste enthalten",
    params=[
        ParamSchema(
            key="days", label="Tage", kind="list_text",
            placeholder="mo,di,mi,do,fr",
        ),
    ],
    evaluate=_evaluate,
))
