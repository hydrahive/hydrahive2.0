import re

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ConditionSpec, ParamSchema, register_condition,
)


def _evaluate(params: dict, event: TriggerEvent) -> bool:
    pattern = (params.get("pattern") or "").strip()
    target = (params.get("target") or "message_text").strip()
    if not pattern:
        return False
    if target == "message_text":
        text = event.message_text or ""
    else:
        text = str(event.payload.get(target, ""))
    try:
        return re.search(pattern, text) is not None
    except re.error:
        return False


register_condition(ConditionSpec(
    subtype="regex_match",
    label="Regex-Treffer",
    description="Regex matcht im Nachrichten-Text oder einem Payload-Feld",
    params=[
        ParamSchema(
            key="pattern", label="Regex", kind="text", required=True,
            placeholder=r"^/help\b",
        ),
        ParamSchema(
            key="target", label="Ziel", kind="text",
            default="message_text",
            placeholder="message_text oder Payload-Feld",
        ),
    ],
    evaluate=_evaluate,
))
