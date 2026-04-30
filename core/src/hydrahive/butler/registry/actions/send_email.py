"""send_email — Phase 2: Stub. Phase 4 nutzt das vorhandene send_mail-Tool."""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.registry.actions._stub import stub_result
from hydrahive.butler.template import render


async def _execute(params: dict, event: TriggerEvent) -> ActionResult:
    rendered = {
        "to": render(params.get("to") or "", event),
        "subject": render(params.get("subject") or "", event),
        "body": render(params.get("body") or "", event),
    }
    return stub_result("send_email", rendered)


register_action(ActionSpec(
    subtype="send_email",
    label="Email senden",
    description="Email senden über die HydraHive-SMTP-Konfiguration",
    params=[
        ParamSchema(key="to", label="An", kind="text", required=True,
                    placeholder="alice@example.com"),
        ParamSchema(key="subject", label="Betreff", kind="text", required=True),
        ParamSchema(key="body", label="Body (Jinja2-Template)", kind="textarea",
                    required=True),
    ],
    execute=_execute,
))
