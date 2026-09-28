"""webhook_received — feuert bei jedem Webhook des Projekts.

Der Endpoint ``POST /api/butler/webhooks/project/{id}`` wählt die Flows schon
projektgenau aus (Scope + Mitglieder + Secret). Ein zusätzlicher Filter über
``hook_id`` passte nie, weil die Oberfläche keinen Doppelpunkt zuließ und der
Kanal ``project:<id>`` heißt. Alte Flows mit ``hook_id`` laufen weiter, der
Wert wird ignoriert.
"""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import TriggerSpec, register_trigger


def _matches(params: dict, event: TriggerEvent) -> bool:
    return event.event_type == "webhook"


register_trigger(TriggerSpec(
    subtype="webhook_received",
    label="Webhook eingegangen",
    description="Feuert bei jedem Webhook des Projekts "
                "(POST /api/butler/webhooks/project/{id}, Header X-Webhook-Secret).",
    params=[],
    matches=_matches,
))
