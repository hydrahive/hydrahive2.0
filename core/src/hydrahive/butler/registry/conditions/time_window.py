from datetime import datetime

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ConditionSpec, ParamSchema, register_condition,
)


def _parse(s: str) -> tuple[int, int] | None:
    try:
        h, m = s.split(":")
        return int(h), int(m)
    except Exception:
        return None


def _evaluate(params: dict, _: TriggerEvent) -> bool:
    a = _parse(params.get("from") or "")
    b = _parse(params.get("to") or "")
    if not a or not b:
        return False
    now = datetime.now()
    cur = now.hour * 60 + now.minute
    start = a[0] * 60 + a[1]
    end = b[0] * 60 + b[1]
    if start <= end:
        return start <= cur <= end
    # Mitternacht-Crossing: 22:00–06:00
    return cur >= start or cur <= end


register_condition(ConditionSpec(
    subtype="time_window",
    label="Zeitfenster",
    description="Lokale Systemzeit zwischen 'from' und 'to' (Mitternacht-Crossing möglich)",
    params=[
        ParamSchema(key="from", label="Von", kind="time", required=True, default="09:00"),
        ParamSchema(key="to", label="Bis", kind="time", required=True, default="17:00"),
    ],
    evaluate=_evaluate,
))
