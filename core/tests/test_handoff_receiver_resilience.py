"""Resilienz-Tests für den AgentLink-Handoff-Empfänger.

Kern-Bug (Subagent-Zombies): ein delegierter Task, der länger läuft als der
Worker lebt (Crash/Reload/Kill) oder der hängt, hinterließ einen permanenten
`in_progress`-State ohne jede Antwort. handoff_receiver muss IMMER einen
terminalen State erzeugen:
  - Run-Timeout      → Fehler-Antwort (kein 600s-Hänger beim Auftraggeber)
  - Cancel/Shutdown  → best-effort Fehler-Antwort, dann re-raise
  - Start            → verwaiste 'running'-Handoffs auf 'error' reconcilen
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink.protocol import ContextBlock, State, TaskBlock
from hydrahive.runner import handoff_receiver as hr


def _state() -> State:
    return State(
        agent_id="auftraggeber",
        task=TaskBlock(type="feature", description="grosse analyse", status="in_progress"),
        context=ContextBlock(files=[], git=None, errors=[]),
    )


def _capture_reply(monkeypatch) -> dict:
    captured: dict = {}

    async def _fake_post_reply(incoming, output, status):
        captured["output"] = output
        captured["status"] = status

    monkeypatch.setattr(hr, "_post_reply", _fake_post_reply)
    monkeypatch.setattr(hr.db_agent_handoffs, "update_status", lambda hid, status: captured.setdefault("db_status", status))
    return captured


# --- Reconciliation beim Start ---------------------------------------------

def test_reconcile_marks_running_handoffs_as_error(monkeypatch):
    running = [{"id": "h1"}, {"id": "h2"}]
    updated: list[tuple[str, str]] = []
    monkeypatch.setattr(hr.db_agent_handoffs, "list_active", lambda: running)
    monkeypatch.setattr(hr.db_agent_handoffs, "update_status", lambda hid, status: updated.append((hid, status)))

    n = hr.reconcile_orphaned_handoffs()

    assert n == 2
    assert updated == [("h1", "error"), ("h2", "error")]


def test_reconcile_noop_when_none_running(monkeypatch):
    monkeypatch.setattr(hr.db_agent_handoffs, "list_active", lambda: [])
    monkeypatch.setattr(hr.db_agent_handoffs, "update_status", lambda hid, status: pytest.fail("darf nicht aufgerufen werden"))
    assert hr.reconcile_orphaned_handoffs() == 0


# --- Run-Timeout: kein stiller Zombie --------------------------------------

def test_run_timeout_posts_error_reply(monkeypatch):
    captured = _capture_reply(monkeypatch)
    monkeypatch.setattr(hr.settings, "agentlink_run_timeout", 0.05, raising=False)

    async def _hang(session_id, user_input, output_parts):
        await asyncio.sleep(5)
        return None

    monkeypatch.setattr(hr, "_consume_run", _hang)

    asyncio.run(hr._run_and_reply(_state(), "sess-1", "hdb-1"))

    assert captured["status"] == "error"
    assert "Timeout" in captured["output"]
    assert captured["db_status"] == "error"


# --- Cancel/Shutdown: best-effort Antwort + re-raise -----------------------

def test_cancelled_run_posts_error_reply_and_reraises(monkeypatch):
    captured = _capture_reply(monkeypatch)
    monkeypatch.setattr(hr.settings, "agentlink_run_timeout", 30, raising=False)

    async def _cancel(session_id, user_input, output_parts):
        raise asyncio.CancelledError()

    monkeypatch.setattr(hr, "_consume_run", _cancel)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(hr._run_and_reply(_state(), "sess-2", "hdb-2"))

    assert captured["status"] == "error"
    assert captured["db_status"] == "error"


# --- Erfolg: done-Antwort ---------------------------------------------------

def test_error_reply_uses_agentlink_compatible_blocked_status(monkeypatch):
    captured: dict = {}

    async def _capture(state):
        captured["state"] = state

    monkeypatch.setattr(hr, "post_state", _capture)

    asyncio.run(hr._post_reply(_state(), "terminaler Fehler", "error"))

    reply = captured["state"]
    assert reply.task.status == "blocked"
    assert reply.task.description.startswith("Fehler:")
    assert reply.working_memory.findings == ["terminaler Fehler"]


def test_error_reply_combines_partial_output_and_terminal_reason(monkeypatch):
    captured = _capture_reply(monkeypatch)
    monkeypatch.setattr(hr.settings, "agentlink_run_timeout", 30, raising=False)

    async def _partial_error(session_id, user_input, output_parts):
        output_parts.append("Bisher geprüft: drei Dateien.")
        return "Max-Iterationen (16) erreicht ohne Abschluss"

    monkeypatch.setattr(hr, "_consume_run", _partial_error)

    asyncio.run(hr._run_and_reply(_state(), "sess-partial", "hdb-partial"))

    assert "Bisher geprüft" in captured["output"]
    assert "Max-Iterationen" in captured["output"]
    assert captured["status"] == "error"


def test_error_reply_bounds_findings_at_live_tool_result_limit(monkeypatch):
    captured: dict = {}

    async def _capture(state):
        captured["state"] = state

    monkeypatch.setattr(hr, "post_state", _capture)

    asyncio.run(hr._post_reply(_state(), "x" * 20_000, "error"))

    assert len(captured["state"].working_memory.findings[0]) == 12_000


def test_successful_run_posts_done_reply(monkeypatch):
    captured = _capture_reply(monkeypatch)
    monkeypatch.setattr(hr.settings, "agentlink_run_timeout", 30, raising=False)

    async def _ok(session_id, user_input, output_parts):
        output_parts.append("OK")
        return None

    monkeypatch.setattr(hr, "_consume_run", _ok)

    asyncio.run(hr._run_and_reply(_state(), "sess-3", "hdb-3"))

    assert captured["status"] == "done"
    assert captured["output"] == "OK"
    assert captured["db_status"] == "done"
