"""Verknüpft eine startende Session mit ihrem Auftraggeber fürs Agenten-Büro (Spec agent-office.md §1).

Eine AgentLink-Handoff-Session trägt `metadata["incoming_state_id"]` (von `_handoff_setup.py` gesetzt).
Darüber findet sich die passende Zeile in `agent_delegations` (Auftraggeber-Session, Delegation-ID) —
ohne neue Spalte, die Daten liegen schon da. Für Chat-Läufe (keine Delegation) liefert es ein leeres
dict, `activity.start(**{})` verhält sich dann wie bisher.
"""
from __future__ import annotations


def activity_start_kwargs(session, agent: dict) -> dict:
    state_id = (session.metadata or {}).get("incoming_state_id")
    if not state_id:
        return {}
    from hydrahive.agentlink.runtime_profiles import effective_budget
    from hydrahive.db import delegations as delegations_db
    row = delegations_db.get_by_state(state_id)
    if not row:
        return {}
    import time
    from hydrahive.runner._run_settings import run_settings
    rs = run_settings(agent)
    budget = effective_budget(agent)
    deadline_at = None
    if row.get("deadline_at"):
        try:
            from datetime import datetime
            deadline_at = datetime.fromisoformat(row["deadline_at"]).timestamp()
        except ValueError:
            deadline_at = None
    return {
        "parent_session_id": row["session_id"],
        "delegation_id": row["id"],
        "max_iterations": rs.max_iterations or budget.max_iterations,
        "deadline_at": deadline_at if deadline_at is not None else time.time() + budget.timeout_seconds,
    }
