"""agent_reply + agent_reply_with_prefix — leiten Nachricht an Agent weiter.
Phase 2: Stub. Phase 4 verkabelt mit Master-Agent-Dispatch."""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.registry.actions._stub import stub_result


async def _exec_plain(params: dict, _: TriggerEvent) -> ActionResult:
    return stub_result("agent_reply", params)


async def _exec_prefix(params: dict, _: TriggerEvent) -> ActionResult:
    return stub_result("agent_reply_with_prefix", params)


_AGENT_ID = ParamSchema(
    key="agent_id", label="Agent", kind="text", required=True,
    placeholder="master oder agent-id",
)

register_action(ActionSpec(
    subtype="agent_reply",
    label="Agent antworten lassen",
    description="Reicht die Nachricht 1:1 an den Agent weiter",
    params=[_AGENT_ID],
    execute=_exec_plain,
))

register_action(ActionSpec(
    subtype="agent_reply_with_prefix",
    label="Agent mit Vorgabe antworten lassen",
    description="Wie agent_reply, aber mit prepended Instruction als Butler-Vorgabe",
    params=[
        _AGENT_ID,
        ParamSchema(
            key="instruction", label="Vorgabe", kind="textarea", required=True,
            placeholder="Antworte freundlich und kurz",
        ),
    ],
    execute=_exec_prefix,
))
