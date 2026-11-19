"""Kette Buddy → Projekt-Agent → Spezialist (Befund 2026-11-19).

Ein per AgentLink-Handoff gestarteter Lauf (origin=handoff) muss seine
Spezialisten im HINTERGRUND beauftragen. Vorher lief ask_agent dort synchron:
der Projekt-Agent wartete, bis sein eigenes Budget (1200 s) ablief, während
der Spezialist (1800 s) weiterarbeitete — Ergebnis verloren
(docs/specs/agent-background-delegation.md, Abschnitt „Kette über Handoff“).
"""
from __future__ import annotations

import asyncio

from hydrahive.agentlink.protocol import ContextBlock, State, TaskBlock
from hydrahive.db import delegations as delegations_db
from hydrahive.runner import delegation_delivery, delegation_watch, handoff_session
from hydrahive.runner import handoff_receiver as hr
from hydrahive.runner._run_origin import handoff as origin_handoff
from hydrahive.tools import _ask_agent_background as bg
from hydrahive.tools import ask_agent
from tests.test_background_delegation import _ctx, _reply, _settle

# Fixtures spec_agent, session_id, agentlink, starter (Muster wie tests/_delete_env.py).
pytest_plugins = ["tests.test_background_delegation"]


def test_handoff_origin_delegates_in_background(spec_agent, session_id, agentlink, starter, tmp_path):
    """Reproduktion: ask_agent aus einem Handoff-Lauf kehrt sofort zurück."""
    posted, futures = agentlink

    async def scenario():
        res = await asyncio.wait_for(
            ask_agent._execute(
                {"goal": "Ziel", "deliverable": "Ergebnis", "agent_id": spec_agent["id"], "task": "bau das"},
                _ctx(session_id, tmp_path, origin="handoff", depth=1),
            ),
            timeout=2,
        )
        assert res.success and res.metadata.get("background") is True
        for t in list(asyncio.all_tasks()):
            if t.get_name().startswith("delegation-"):
                t.cancel()

    asyncio.run(scenario())
    d = delegations_db.list_for_session(session_id)[0]
    assert d["depth"] == 2


# --- Ganzer Weg: Handoff-Lauf → Kind im Hintergrund → Folgelauf → EINE Antwort ---------------------


def _incoming() -> State:
    return State(id="st-in-1", agent_id="hydrahive/buddy",
                 task=TaskBlock(type="feature", description="Phase 3 bauen", status="in_progress"),
                 context=ContextBlock(files=[], git=None, errors=[]))


def _wire_chain(monkeypatch, session_id, spec_agent, tmp_path, *, followup_text="Fertig: alles gebaut."):
    """Ersetzt nur die LLM-Läufe. ask_agent, Delegations-DB, Watcher, Zustellung,
    Ketten-Logik und Antwort-Weg laufen echt."""
    replies: list[dict] = []
    runs: list[str] = []

    async def fake_post_reply(incoming, output, status, **kw):
        replies.append({"output": output, "status": status})
        return True

    async def fake_consume(sid, user_input, output_parts, *, origin=None):
        runs.append(user_input)
        assert origin is not None and origin.kind == "handoff"
        if len(runs) == 1:
            # Erster Lauf: Projekt-Agent verteilt an den Spezialisten und endet.
            res = await ask_agent._execute(
                {"goal": "Backend", "deliverable": "Bericht", "agent_id": spec_agent["id"], "task": "Backend bauen"},
                _ctx(sid, tmp_path, origin="handoff", depth=origin.depth),
            )
            assert res.success and res.metadata.get("background") is True, res.error
            output_parts.append("Vergeben an Prüfer.")
        else:
            output_parts.append(followup_text)
        return None

    monkeypatch.setattr(hr, "_post_reply", fake_post_reply)
    monkeypatch.setattr(hr, "_consume_run", fake_consume)
    monkeypatch.setattr(hr.db_agent_handoffs, "update_status", lambda *a, **k: None)
    monkeypatch.setattr(hr, "_shorten", lambda raw, *a, **k: raw)
    return replies, runs


def test_full_chain_replies_once_after_child_result(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path)

    async def scenario():
        handoff_session.mark_started(session_id)
        await hr._run_and_reply(_incoming(), session_id, "hdb-1", run_timeout=30, origin=origin_handoff(1))
        # Erster Lauf ist vorbei, Spezialist arbeitet noch → KEINE Antwort, Kette offen.
        assert replies == [] and handoff_session.is_open(session_id)
        next(iter(futures.values())).set_result(_reply("Backend fertig, 12 Tests grün."))
        await _settle(lambda: len(replies) == 1, timeout=5)

    asyncio.run(scenario())
    assert len(runs) == 2                                   # erster Lauf + Auswertungslauf
    assert "Backend fertig, 12 Tests grün." in runs[1]      # Kind-Ergebnis kam beim Projekt-Agenten an
    assert replies[0]["status"] == "done"
    assert replies[0]["output"] == "Fertig: alles gebaut."  # EINE Antwort mit dem Abschlussbericht
    assert starter == []                                    # kein Chat-Lauf im Projekt-Agenten
    assert not handoff_session.is_open(session_id)
    assert delegations_db.list_for_session(session_id)[0]["delivered_at"] is not None


def test_child_already_done_before_first_run_ends(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    """Rennen: Kind fertig, während der erste Lauf noch läuft → trotzdem ausgewertet."""
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path)
    original = hr._consume_run

    async def consume_and_finish_child(sid, user_input, output_parts, *, origin=None):
        r = await original(sid, user_input, output_parts, origin=origin)
        if len(runs) == 1:
            d = delegations_db.list_for_session(sid)[0]
            delegations_db.complete_by_state(d["state_id"], "done", "schnell fertig")
        return r

    monkeypatch.setattr(hr, "_consume_run", consume_and_finish_child)

    async def scenario():
        await hr._run_and_reply(_incoming(), session_id, "hdb-2", run_timeout=30, origin=origin_handoff(1))
        await _settle(lambda: len(replies) == 1, timeout=5)
        for t in list(delegation_watch._tasks.values()):
            t.cancel()

    asyncio.run(scenario())
    assert len(runs) == 2 and "schnell fertig" in runs[1]
    assert replies[0]["status"] == "done"


def test_child_error_is_evaluated_not_lost(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path,
                                followup_text="Spezialist scheiterte: Migration fehlt.")

    async def scenario():
        await hr._run_and_reply(_incoming(), session_id, "hdb-3", run_timeout=30, origin=origin_handoff(1))
        d = delegations_db.list_for_session(session_id)[0]
        delegations_db.complete_by_state(d["state_id"], "error", "Migration 010 fehlt")
        delegation_delivery.kick(session_id)
        await _settle(lambda: len(replies) == 1, timeout=5)
        for t in list(delegation_watch._tasks.values()):
            t.cancel()

    asyncio.run(scenario())
    assert "Migration 010 fehlt" in runs[1]
    assert replies[0]["output"].startswith("Spezialist scheiterte")


def test_chain_deadline_answers_and_cancels_children(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    """Gesamtfrist: Antwort mit bisherigem Stand, offene Kinder abgebrochen."""
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path)
    monkeypatch.setattr(handoff_session, "CHAIN_TOTAL_SECONDS", 0)
    monkeypatch.setattr(handoff_session.ChainState, "remaining", lambda self: 0.05)

    async def scenario():
        await hr._run_and_reply(_incoming(), session_id, "hdb-4", run_timeout=30, origin=origin_handoff(1))
        await _settle(lambda: len(replies) == 1, timeout=5)

    asyncio.run(scenario())
    assert replies[0]["status"] == "error"
    assert "Vergeben an Prüfer." in replies[0]["output"] and "Gesamtfrist" in replies[0]["output"]
    assert delegations_db.list_for_session(session_id)[0]["status"] == "cancelled"
    assert not handoff_session.is_open(session_id)


def test_failed_first_run_replies_immediately_and_cancels_children(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path)
    ok_consume = hr._consume_run

    async def consume_then_fail(sid, user_input, output_parts, *, origin=None):
        await ok_consume(sid, user_input, output_parts, origin=origin)
        return hr.RunFailure("Modell-Fehler")

    monkeypatch.setattr(hr, "_consume_run", consume_then_fail)
    asyncio.run(hr._run_and_reply(_incoming(), session_id, "hdb-5", run_timeout=30, origin=origin_handoff(1)))
    assert len(replies) == 1 and replies[0]["status"] == "error"
    assert delegations_db.list_for_session(session_id)[0]["status"] == "cancelled"
    assert not handoff_session.is_open(session_id)


def test_non_handoff_run_never_holds_reply(session_id, monkeypatch):
    """Spezialist ohne Kinder / Läufe anderer Herkunft: sofort antworten wie bisher."""
    replies: list = []

    async def fake_post_reply(incoming, output, status, **kw):
        replies.append(status)
        return True

    async def ok(sid, ui, parts, **kw):
        parts.append("x")

    monkeypatch.setattr(hr, "_post_reply", fake_post_reply)
    monkeypatch.setattr(hr, "_consume_run", ok)
    monkeypatch.setattr(hr.db_agent_handoffs, "update_status", lambda *a, **k: None)
    asyncio.run(hr._run_and_reply(_incoming(), session_id, "hdb-6", run_timeout=30, origin=origin_handoff(2)))
    assert replies == ["done"] and not handoff_session.is_open(session_id)


def test_background_origins_single_source():
    from hydrahive.runner._run_origin import RunOrigin
    for kind in ("chat", "delegation", "handoff", "other"):
        assert RunOrigin(kind).background_allowed == (kind in bg.BACKGROUND_ORIGINS)


def test_caller_waits_chain_deadline_for_delegating_target(monkeypatch):
    from hydrahive.agentlink import runtime_profiles as rp
    from hydrahive.tools._ask_agent_helpers import response_timeout
    budget = rp.RuntimeBudget(version=1, profile="template", max_iterations=60, max_tokens=1, timeout_seconds=1200)
    monkeypatch.setattr("hydrahive.tools._ask_agent_helpers.effective_budget", lambda *a: budget)
    assert response_timeout({"id": "p", "tools": ["ask_agent"]}, "template") == rp.CHAIN_TOTAL_SECONDS + 60
    assert response_timeout({"id": "s", "tools": ["file_read"]}, "template") == 1200 + 60


def test_followup_handoff_does_not_take_over_open_chain_session(session_id):
    from hydrahive.runner import _handoff_setup
    handoff_session.open_chain(handoff_session.ChainState(
        state=_incoming(), session_id=session_id, handoff_db_id="h", run_timeout=1, depth=1))
    try:
        assert _handoff_setup._running(session_id) is True
    finally:
        handoff_session.close_chain(session_id)


def test_followup_prompt_asks_for_final_report_not_user_info(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path)

    async def scenario():
        await hr._run_and_reply(_incoming(), session_id, "hdb-7", run_timeout=30, origin=origin_handoff(1))
        next(iter(futures.values())).set_result(_reply("ok"))
        await _settle(lambda: len(replies) == 1, timeout=5)

    asyncio.run(scenario())
    assert "Abschlussbericht" in runs[1] and "informiere den Nutzer" not in runs[1]


def test_handoff_ask_agent_reply_says_end_run_not_tell_user(spec_agent, session_id, agentlink, starter, tmp_path):
    async def scenario():
        res = await ask_agent._execute(
            {"goal": "Ziel", "deliverable": "Ergebnis", "agent_id": spec_agent["id"], "task": "x"},
            _ctx(session_id, tmp_path, origin="handoff", depth=1))
        for t in list(delegation_watch._tasks.values()):
            t.cancel()
        return res

    out = asyncio.run(scenario()).output
    assert "Abschlussbericht" in out and "Sag dem Nutzer" not in out


def test_max_iterations_with_running_children_keeps_chain(spec_agent, session_id, agentlink, starter, tmp_path, monkeypatch):
    """Iterationsgrenze nach dem Verteilen ist kein Abbruch: Kette wartet weiter."""
    posted, futures = agentlink
    replies, runs = _wire_chain(monkeypatch, session_id, spec_agent, tmp_path)
    ok_consume = hr._consume_run

    async def consume_hits_limit(sid, user_input, output_parts, *, origin=None):
        await ok_consume(sid, user_input, output_parts, origin=origin)
        if len(runs) == 1:
            return hr.RunFailure("Max-Iterationen", "max_iterations")
        return None

    monkeypatch.setattr(hr, "_consume_run", consume_hits_limit)

    async def scenario():
        await hr._run_and_reply(_incoming(), session_id, "hdb-8", run_timeout=30, origin=origin_handoff(1))
        assert replies == [] and handoff_session.is_open(session_id)
        assert delegations_db.list_for_session(session_id)[0]["status"] == "running"
        next(iter(futures.values())).set_result(_reply("fertig"))
        await _settle(lambda: len(replies) == 1, timeout=5)

    asyncio.run(scenario())
    assert replies[0]["status"] == "done" and replies[0]["output"] == "Fertig: alles gebaut."
