"""Prepare new or resumed AgentLink handoff sessions without starting the run."""
from __future__ import annotations

from dataclasses import dataclass

from hydrahive.agentlink.protocol import State
from hydrahive.agentlink.runtime_profiles import (
    RUNTIME_METADATA_KEY,
    effective_budget,
    profile_from_reason,
    resume_token_from_reason,
)
from hydrahive.db import agent_handoffs as db_agent_handoffs
from hydrahive.db import sessions as sessions_db


class HandoffSetupError(RuntimeError):
    """Safe, caller-facing setup error."""


@dataclass(frozen=True, slots=True)
class PreparedHandoff:
    session_id: str
    handoff_id: str
    timeout_seconds: int
    resumed: bool
    resume_token: str | None = None


def _resume_requested(reason: str) -> bool:
    return any(segment.startswith("hh-resume:") for segment in reason.split("|"))


def _resume_session(state: State, target: dict, reason: str, budget):
    token = resume_token_from_reason(reason)
    if not token:
        raise HandoffSetupError("Ungültiges oder inkompatibles Resume-Token")
    previous = db_agent_handoffs.get_resumable(
        token, from_agent=state.agent_id, agent_id=target["id"],
    )
    if not previous:
        raise HandoffSetupError("Resume-Token unbekannt, fremd oder bereits verwendet")
    session = sessions_db.get(previous["session_id"])
    if not session or session.agent_id != target["id"]:
        raise HandoffSetupError("Checkpoint-Session nicht mehr verfügbar")
    claimed = db_agent_handoffs.claim_resumable(
        token, from_agent=state.agent_id, agent_id=target["id"],
    )
    if not claimed:
        raise HandoffSetupError("Resume-Token wurde bereits gleichzeitig verwendet")
    metadata = dict(session.metadata or {})
    metadata[RUNTIME_METADATA_KEY] = budget.as_metadata()
    metadata["incoming_state_id"] = state.id
    try:
        sessions_db.update(session.id, status="active", metadata=metadata)
    except Exception as exc:
        db_agent_handoffs.restore_paused_claim(token)
        raise HandoffSetupError("Handoff konnte nicht sicher gestartet werden") from exc
    return session, token


def _new_session(state: State, target: dict, budget):
    owner = target.get("owner") or "admin"
    return sessions_db.create(
        agent_id=target["id"],
        user_id=owner,
        project_id=target.get("project_id"),
        title=(state.task.description or "AgentLink-Task")[:80],
        metadata={
            "source": "agentlink", "incoming_state_id": state.id,
            RUNTIME_METADATA_KEY: budget.as_metadata(),
        },
    )


def prepare_handoff(state: State, target: dict, reason: str) -> PreparedHandoff:
    """Validate, claim and persist a handoff before the async run is scheduled."""
    budget = effective_budget(target, profile_from_reason(reason))
    resumed = _resume_requested(reason)
    resume_token: str | None = None
    handoff_record: dict | None = None
    claim_acquired = False
    try:
        if resumed:
            session, resume_token = _resume_session(state, target, reason, budget)
            claim_acquired = True
        else:
            session = _new_session(state, target, budget)
        handoff_record = db_agent_handoffs.create(
            incoming_state_id=state.id or "",
            from_agent=state.agent_id,
            agent_id=target["id"],
            session_id=session.id,
        )
        return PreparedHandoff(
            session_id=session.id,
            handoff_id=handoff_record["id"],
            timeout_seconds=budget.timeout_seconds,
            resumed=resumed,
            resume_token=resume_token,
        )
    except HandoffSetupError:
        raise
    except Exception as exc:
        if handoff_record:
            db_agent_handoffs.update_status(handoff_record["id"], "error")
        if claim_acquired and resume_token:
            db_agent_handoffs.restore_paused_claim(resume_token)
        raise HandoffSetupError("Handoff konnte nicht sicher gestartet werden") from exc


def rollback_prepared(prepared: PreparedHandoff) -> None:
    """Undo a prepared resume if scheduling fails before the coroutine starts."""
    db_agent_handoffs.update_status(prepared.handoff_id, "error")
    if prepared.resume_token:
        db_agent_handoffs.restore_paused_claim(prepared.resume_token)
