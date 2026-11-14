"""activity.start() mit Delegations-Hierarchie und Budget für laufende AgentLink-Handoffs (Spec agent-office.md §1)."""
from __future__ import annotations

import time

from hydrahive.agents import config as agent_config
from hydrahive.db import delegations as delegations_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner._activity_link import activity_start_kwargs


def test_ohne_handoff_leere_zusatzfelder(client):
    a = agent_config.create(agent_type="specialist", name="X", llm_model="m", owner="u",
                            temperature=0.7, max_tokens=1024, thinking_budget=0)
    s = sessions_db.create(agent_id=a["id"], user_id="u")
    assert activity_start_kwargs(s, a) == {}
    agent_config.delete(a["id"])


def test_mit_handoff_liefert_eltern_session_und_delegation(client):
    caller = agent_config.create(agent_type="specialist", name="Caller", llm_model="m", owner="u",
                                 temperature=0.7, max_tokens=1024, thinking_budget=0)
    target = agent_config.create(agent_type="specialist", name="Target", llm_model="m", owner="u",
                                 temperature=0.7, max_tokens=1024, thinking_budget=0)
    caller_session = sessions_db.create(agent_id=caller["id"], user_id="u")
    row = delegations_db.create(
        session_id=caller_session.id, agent_id=caller["id"], user_id="u",
        target_agent_id=target["id"], target_name="Target", task="prüf das",
        state_id="st-xyz", depth=1, timeout_seconds=540,
    )
    target_session = sessions_db.create(
        agent_id=target["id"], user_id="u", metadata={"incoming_state_id": "st-xyz",
                                                      "hh_runtime": {"timeout_seconds": 540}})
    kw = activity_start_kwargs(target_session, target)
    assert kw["parent_session_id"] == caller_session.id
    assert kw["delegation_id"] == row["id"]
    assert kw["max_iterations"] > 0
    assert kw["deadline_at"] is not None and kw["deadline_at"] > time.time()
    agent_config.delete(caller["id"])
    agent_config.delete(target["id"])


def test_unbekannter_state_id_bleibt_leer(client):
    a = agent_config.create(agent_type="specialist", name="Y", llm_model="m", owner="u",
                            temperature=0.7, max_tokens=1024, thinking_budget=0)
    s = sessions_db.create(agent_id=a["id"], user_id="u", metadata={"incoming_state_id": "unbekannt-123"})
    assert activity_start_kwargs(s, a) == {}
    agent_config.delete(a["id"])
