from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ConditionSpec, ParamSchema, register_condition,
)


def _evaluate(params: dict, event: TriggerEvent) -> bool:
    keyword = (params.get("keyword") or "").strip().lower()
    if not keyword or not event.message_text:
        return False
    return keyword in event.message_text.lower()


register_condition(ConditionSpec(
    subtype="message_contains",
    label="Nachricht enthält",
    description="Substring (case-insensitive) im Nachrichten-Text",
    params=[
        ParamSchema(
            key="keyword", label="Schlüsselwort", kind="text", required=True,
        ),
    ],
    evaluate=_evaluate,
))
