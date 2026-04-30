"""payload_field_equals + payload_field_contains — JSON-Pfad-Navigation."""
from typing import Any

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ConditionSpec, ParamSchema, register_condition,
)


def _walk(obj: Any, path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def _eval_equals(params: dict, event: TriggerEvent) -> bool:
    field = (params.get("field") or "").strip()
    expected = params.get("value")
    if not field:
        return False
    actual = _walk(event.payload, field)
    return str(actual) == str(expected)


def _eval_contains(params: dict, event: TriggerEvent) -> bool:
    field = (params.get("field") or "").strip()
    needle = (params.get("value") or "").strip()
    if not field or not needle:
        return False
    actual = _walk(event.payload, field)
    return actual is not None and needle.lower() in str(actual).lower()


_FIELD = ParamSchema(
    key="field", label="Feld (Punkt-Notation)", kind="text",
    placeholder="pull_request.state", required=True,
)
_VALUE = ParamSchema(key="value", label="Wert", kind="text", required=True)

register_condition(ConditionSpec(
    subtype="payload_field_equals",
    label="Payload-Feld =",
    description="Feld im Event-Payload exakt gleich dem Wert (Punkt-Notation für JSON-Pfad)",
    params=[_FIELD, _VALUE], evaluate=_eval_equals,
))

register_condition(ConditionSpec(
    subtype="payload_field_contains",
    label="Payload-Feld enthält",
    description="Feld im Event-Payload enthält den Wert (case-insensitive Substring)",
    params=[_FIELD, _VALUE], evaluate=_eval_contains,
))
