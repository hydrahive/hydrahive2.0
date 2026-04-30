from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ConditionSpec, ParamSchema, register_condition,
)


def _evaluate(params: dict, event: TriggerEvent) -> bool:
    raw = params.get("contacts") or []
    if isinstance(raw, str):
        contacts = [c.strip() for c in raw.split(",") if c.strip()]
    elif isinstance(raw, list):
        contacts = [str(c).strip() for c in raw if str(c).strip()]
    else:
        return False
    if not contacts or not event.contact_id:
        return False
    cid = event.contact_id.lower()
    return any(c.lower() == cid for c in contacts)


register_condition(ConditionSpec(
    subtype="contact_in_list",
    label="Kontakt in Liste",
    description="Sender-ID/Email in einer kommaseparierten Liste",
    params=[
        ParamSchema(
            key="contacts", label="Kontakte (komma-sep)", kind="textarea",
            placeholder="491234567890, alice@example.com", required=True,
        ),
    ],
    evaluate=_evaluate,
))
