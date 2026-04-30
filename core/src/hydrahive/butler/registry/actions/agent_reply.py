"""agent_reply + agent_reply_with_prefix — leiten Nachricht an Agent weiter.

Action selbst ruft den Agent NICHT — sie liefert die Routing-Info als
`reply_via_agent` + optional `reply_prefix`. Der Channel-Router führt
den Agent-Run aus damit der IncomingEvent-Kontext (Session, Channel)
korrekt verkabelt ist.

`agent_reply_guided` ist ein Alias auf agent_reply_with_prefix damit der
alte Frontend-Code (octopos) ohne Änderung mit dem neuen Backend redet.
"""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.template import render


async def _exec_plain(params: dict, _: TriggerEvent) -> ActionResult:
    agent_id = (params.get("agent_id") or "").strip()
    if not agent_id:
        # Kein Agent gewählt → Action ist nicht actionable, also den Master
        # NICHT überschreiben — sonst stille Failure für den User.
        return ActionResult(ok=False, detail="agent_id_missing", stop_default=False)
    return ActionResult(
        ok=True, detail="agent_reply",
        reply_via_agent=agent_id, stop_default=True,
    )


async def _exec_prefix(params: dict, event: TriggerEvent) -> ActionResult:
    agent_id = (params.get("agent_id") or "").strip()
    if not agent_id:
        return ActionResult(ok=False, detail="agent_id_missing", stop_default=False)
    prefix = render(params.get("instruction") or "", event)
    return ActionResult(
        ok=True, detail="agent_reply_with_prefix",
        reply_via_agent=agent_id,
        reply_prefix=prefix or None,
        stop_default=True,
    )


_AGENT_ID = ParamSchema(
    key="agent_id", label="Agent", kind="text", required=True,
    placeholder="master oder agent-id",
)
_PREFIX = ParamSchema(
    key="instruction", label="Vorgabe", kind="textarea", required=True,
    placeholder="Antworte freundlich und kurz",
)

register_action(ActionSpec(
    subtype="agent_reply",
    label="Agent antworten lassen",
    description="Reicht die Nachricht 1:1 an den Agent weiter",
    params=[_AGENT_ID],
    execute=_exec_plain,
))

# Alias für altes UI: agent_reply_guided == agent_reply_with_prefix
register_action(ActionSpec(
    subtype="agent_reply_with_prefix",
    label="Agent mit Vorgabe antworten lassen",
    description="Wie agent_reply, aber mit prepended Instruction",
    params=[_AGENT_ID, _PREFIX],
    execute=_exec_prefix,
))

register_action(ActionSpec(
    subtype="agent_reply_guided",
    label="Agent mit Vorgabe antworten lassen",
    description="Alias für agent_reply_with_prefix (alter Frontend-Code)",
    params=[_AGENT_ID, _PREFIX],
    execute=_exec_prefix,
))


# `forward` aus dem alten UI ist ein Alias für agent_reply
async def _exec_forward(params: dict, ev: TriggerEvent) -> ActionResult:
    return await _exec_plain(params, ev)


register_action(ActionSpec(
    subtype="forward",
    label="An Agent weiterleiten",
    description="Alias für agent_reply",
    params=[_AGENT_ID],
    execute=_exec_forward,
))
