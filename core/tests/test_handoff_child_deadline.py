"""Kind-Aufträge einer Handoff-Kette leben nie länger als die Kette selbst.

Befund 19.11.2026 (Auftrag a3bd510c): Die Gesamtfrist der Kette (60 min) war
fast abgelaufen, der Projekt-Agent vergab trotzdem einen Folgeauftrag mit
„Frist ca. 31 min“. Sekunden später brach die Kette ihn mit ab, der Bericht
versprach aber, der Rest sei vergeben. Jetzt: Frist des Kindes auf die
Restzeit gekürzt, unter MIN_CHILD_SECONDS wird nicht mehr vergeben.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime

from hydrahive.db import delegations as delegations_db
from hydrahive.runner import handoff_session
from hydrahive.tools import _ask_agent_background as bg
from hydrahive.tools import ask_agent
from tests.test_background_delegation import _ctx

pytest_plugins = ["tests.test_background_delegation"]

_ARGS = {"goal": "Ziel", "deliverable": "Ergebnis", "task": "bau das"}


def _chain_started(session_id: str, seconds_ago: float) -> None:
    handoff_session.mark_started(session_id)
    handoff_session._started[session_id] = time.monotonic() - seconds_ago


def _run(session_id, spec_agent, tmp_path, origin="handoff"):
    async def scenario():
        res = await ask_agent._execute({**_ARGS, "agent_id": spec_agent["id"]},
                                       _ctx(session_id, tmp_path, origin=origin, depth=1))
        for t in list(asyncio.all_tasks()):
            if t.get_name().startswith("delegation-"):
                t.cancel()
        return res
    return asyncio.run(scenario())


def _frist_seconds(session_id: str) -> float:
    d = delegations_db.list_for_session(session_id)[0]
    return (datetime.fromisoformat(d["deadline_at"]) - datetime.fromisoformat(d["created_at"])).total_seconds()


def test_child_refused_when_chain_almost_over(spec_agent, session_id, agentlink, starter, tmp_path):
    """Reproduktion: 1 min Restzeit → kein Auftrag, kein Spezialist läuft umsonst."""
    posted, _ = agentlink
    _chain_started(session_id, handoff_session.CHAIN_TOTAL_SECONDS - 60)
    try:
        res = _run(session_id, spec_agent, tmp_path)
    finally:
        handoff_session.forget(session_id)
    assert res.success is False and "Gesamtfrist" in res.error
    assert posted == []
    assert delegations_db.list_for_session(session_id) == []


def test_child_deadline_capped_to_chain_remaining(spec_agent, session_id, agentlink, starter, tmp_path,
                                                   monkeypatch):
    """Kind-Budget 30 min, Kette noch 8 min → Kind bekommt 8 min (wie a3bd510c: 31 min bei ~0 Rest)."""
    monkeypatch.setattr(ask_agent, "_response_timeout", lambda *_a, **_k: 1860)
    _chain_started(session_id, handoff_session.CHAIN_TOTAL_SECONDS - 480)
    try:
        res = _run(session_id, spec_agent, tmp_path)
    finally:
        handoff_session.forget(session_id)
    assert res.success and res.metadata.get("background") is True
    assert 470 <= _frist_seconds(session_id) <= 482
    assert "Frist ca. 8 min" in res.output


def test_fresh_chain_keeps_full_child_budget(spec_agent, session_id, agentlink, starter, tmp_path):
    """Kette frisch gestartet → Kind-Frist unverändert (kein Nebeneffekt)."""
    _chain_started(session_id, 0)
    try:
        res = _run(session_id, spec_agent, tmp_path)
    finally:
        handoff_session.forget(session_id)
    assert res.success
    full = ask_agent._response_timeout(spec_agent, "standard")
    assert abs(_frist_seconds(session_id) - full) <= 5


def test_chat_origin_is_not_limited_by_chain(spec_agent, session_id, agentlink, starter, tmp_path):
    """Im Chat gibt es keine Kette → keine Kürzung, auch wenn eine Startzeit gesetzt wäre."""
    _chain_started(session_id, handoff_session.CHAIN_TOTAL_SECONDS - 60)
    try:
        res = _run(session_id, spec_agent, tmp_path, origin="chat")
    finally:
        handoff_session.forget(session_id)
    assert res.success


def test_remaining_seconds_none_without_chain(session_id):
    handoff_session.forget(session_id)
    assert handoff_session.remaining_seconds(session_id) is None


def test_min_child_seconds_is_meaningful():
    assert 60 <= bg.MIN_CHILD_SECONDS < handoff_session.CHAIN_TOTAL_SECONDS
