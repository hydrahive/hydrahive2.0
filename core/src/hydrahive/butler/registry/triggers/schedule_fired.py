"""Trigger emitted by persistent scheduled tasks."""
from __future__ import annotations

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import ParamSchema, TriggerSpec, register_trigger


def _matches(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "schedule":
        return False
    wanted = str(params.get("schedule_id") or "").strip()
    if wanted and event.payload.get("schedule_id") != wanted:
        return False
    wanted_agent = str(params.get("agent_id") or "all").strip()
    return wanted_agent in ("", "all") or event.payload.get("agent_id") == wanted_agent


_SPEC = TriggerSpec(
    subtype="schedule_fired",
    label="Intervallaufgabe ausgelöst",
    description="Wird durch eine geplante Intervallaufgabe ausgelöst.",
    params=[
        ParamSchema(key="schedule_id", label="Zeitplan-ID", kind="text", placeholder="optional"),
        ParamSchema(key="agent_id", label="Agent-ID", kind="text", default="all"),
    ],
    matches=_matches,
)
register_trigger(_SPEC)

# Backwards-compatible name for the old Butler palette and saved flows.
register_trigger(TriggerSpec(
    subtype="heartbeat_fired", label="Heartbeat-Aufgabe", description=_SPEC.description,
    params=_SPEC.params, matches=_matches,
))
