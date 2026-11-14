"""Folgeauftrag im selben Vorgang setzt die Sitzung des Spezialisten fort (Plan E6 T4)."""
from __future__ import annotations

import pytest

from hydrahive.agentlink.protocol import Handoff, State, TaskBlock
from hydrahive.agentlink.runtime_profiles import reason_with_profile, thread_from_reason, thread_key
from hydrahive.agents import config as agent_config
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import _handoff_setup as hs


@pytest.fixture
def target(client):
    a = agent_config.create(agent_type="specialist", name="Folge Ziel", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1024, thinking_budget=0)
    yield a
    agent_config.delete(a["id"])


def _state(sid: str, desc: str = "Auftrag", sender: str = "hh-agent-a") -> State:
    return State(id=sid, agent_id=sender, task=TaskBlock(type="feature", description=desc, status="in_progress"),
                 handoff=Handoff(to_agent="hydrahive", reason=""))


def _reason(target_id: str, caller_session: str | None) -> str:
    return reason_with_profile(target_id, "standard", "x", thread=thread_key(caller_session) if caller_session else None)


def test_thread_im_reason_und_nicht_einschleusbar():
    r = _reason("t1", "sess-123")
    assert thread_from_reason(r) == thread_key("sess-123")
    assert thread_from_reason("hh-target:t|hh-task: x|hh-thread:v1:boese") is None   # nach hh-task zählt nichts
    assert thread_key("a") != thread_key("b") and len(thread_key("a")) == 24


def test_folgeauftrag_setzt_sitzung_fort(target):
    from hydrahive.db import agent_handoffs
    first = hs.prepare_handoff(_state("st-1"), target, _reason(target["id"], "auftraggeber-1"))
    assert first.resumed is False
    agent_handoffs.update_status(first.handoff_id, "done")                 # Lauf beendet (handoff_receiver)
    second = hs.prepare_handoff(_state("st-2", "Folgeauftrag"), target, _reason(target["id"], "auftraggeber-1"))
    assert second.session_id == first.session_id and second.continued is True
    assert sessions_db.get(second.session_id).metadata["incoming_state_id"] == "st-2"


def test_anderer_vorgang_neue_sitzung(target):
    a = hs.prepare_handoff(_state("st-3"), target, _reason(target["id"], "auftraggeber-2"))
    b = hs.prepare_handoff(_state("st-4"), target, _reason(target["id"], "auftraggeber-3"))
    assert a.session_id != b.session_id


def test_anderer_absender_bekommt_fremde_sitzung_nicht(target):
    from hydrahive.db import agent_handoffs
    a = hs.prepare_handoff(_state("st-5", sender="hh-agent-a"), target, _reason(target["id"], "auftraggeber-4"))
    agent_handoffs.update_status(a.handoff_id, "done")
    b = hs.prepare_handoff(_state("st-6", sender="hh-agent-b"), target, _reason(target["id"], "auftraggeber-4"))
    assert a.session_id != b.session_id


def test_laufende_sitzung_wird_nicht_fortgesetzt(target, monkeypatch):
    from hydrahive.db import agent_handoffs
    a = hs.prepare_handoff(_state("st-7"), target, _reason(target["id"], "auftraggeber-5"))
    agent_handoffs.update_status(a.handoff_id, "done")
    monkeypatch.setattr(hs, "_running", lambda sid: sid == a.session_id)
    b = hs.prepare_handoff(_state("st-8"), target, _reason(target["id"], "auftraggeber-5"))
    assert b.session_id != a.session_id


def test_ohne_thread_wie_bisher(target):
    a = hs.prepare_handoff(_state("st-9"), target, _reason(target["id"], None))
    b = hs.prepare_handoff(_state("st-10"), target, _reason(target["id"], None))
    assert a.session_id != b.session_id
