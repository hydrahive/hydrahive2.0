"""Tests für compaction_events — DB-Roundtrip + compact_session-Hook (Token-Audit #129)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from hydrahive.compaction.compactor import compact_session
from hydrahive.db import compaction_events as compaction_events_db
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db


def _make_session() -> str:
    init_db()
    s = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="compaction-test")
    return s.id


def test_insert_und_for_session_roundtrip(setup_test_env):
    session_id = _make_session()
    ev = compaction_events_db.CompactionEvent(
        session_id=session_id,
        agent_id="test-agent-001",
        user_id="testuser",
        triggered_by="auto",
        trigger_threshold_pct=75,
        model="claude-sonnet-4-7",
        source="default",
        instructions=None,
        tool_result_limit=None,
        skipped=False,
        skip_reason=None,
        skip_reason_params=None,
        messages_total=10,
        messages_visible_before=10,
        messages_to_summarize=6,
        messages_kept=4,
        tokens_before=120_000,
        tokens_after_estimate=25_000,
        cut_kept_from_index=6,
        cut_is_split_turn=False,
        cut_turn_prefix_count=0,
        summary_chars=1500,
        summary_tokens_estimate=375,
        facts_count=3,
        files_extracted_count=2,
        compaction_message_id="msg_abc123",
        had_previous_summary=False,
        duration_ms=4200,
        error=None,
    )
    ev_id = compaction_events_db.insert(ev)
    assert ev_id.startswith("cmpe_")

    rows = compaction_events_db.for_session(session_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == ev_id
    assert row["triggered_by"] == "auto"
    assert row["trigger_threshold_pct"] == 75
    assert row["skipped"] == 0
    assert row["messages_to_summarize"] == 6
    assert row["tokens_before"] == 120_000
    assert row["cut_is_split_turn"] == 0
    assert row["duration_ms"] == 4200
    assert row["error"] is None


def test_skip_reason_params_als_json_persistiert(setup_test_env):
    import json as _json
    session_id = _make_session()
    ev = compaction_events_db.CompactionEvent(
        session_id=session_id,
        agent_id=None, user_id=None,
        triggered_by="auto", trigger_threshold_pct=None,
        model=None, source=None,
        instructions=None, tool_result_limit=None,
        skipped=True,
        skip_reason="cancelled_by_hook",
        skip_reason_params={"hook": "memory_flush"},
        messages_total=None, messages_visible_before=None,
        messages_to_summarize=None, messages_kept=None,
        tokens_before=None, tokens_after_estimate=None,
        cut_kept_from_index=None, cut_is_split_turn=None, cut_turn_prefix_count=None,
        summary_chars=None, summary_tokens_estimate=None,
        facts_count=None, files_extracted_count=None,
        compaction_message_id=None, had_previous_summary=None,
        duration_ms=12, error=None,
    )
    compaction_events_db.insert(ev)
    row = compaction_events_db.for_session(session_id)[0]
    assert row["skipped"] == 1
    assert row["skip_reason"] == "cancelled_by_hook"
    assert _json.loads(row["skip_reason_params"]) == {"hook": "memory_flush"}


def test_latest_for_session_liefert_neuestes_event(setup_test_env):
    from hydrahive.db.connection import db

    session_id = _make_session()
    with db() as conn:
        conn.execute(
            "INSERT INTO compaction_events (id, session_id, created_at, skipped, error) VALUES (?, ?, ?, ?, ?)",
            ("cmpe_old", session_id, "2026-11-09T10:00:00.000+00:00", 0, "RateLimitError"),
        )
        conn.execute(
            "INSERT INTO compaction_events (id, session_id, created_at, skipped, error) VALUES (?, ?, ?, ?, ?)",
            ("cmpe_new", session_id, "2026-11-09T10:05:00.000+00:00", 0, None),
        )

    latest = compaction_events_db.latest_for_session(session_id)
    assert latest is not None
    assert latest["id"] == "cmpe_new"
    assert compaction_events_db.latest_for_session("unknown") is None


def test_compact_session_loggt_too_short_skip(setup_test_env):
    """compact_session mit < 4 Messages → skipped=too_short, eine Zeile in compaction_events."""
    session_id = _make_session()

    result = asyncio.run(compact_session(
        session_id, model="claude-sonnet-4-7",
        triggered_by="auto", trigger_threshold_pct=75,
    ))
    assert result == {"skipped": True, "reason_code": "too_short"}

    rows = compaction_events_db.for_session(session_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["skipped"] == 1
    assert row["skip_reason"] == "too_short"
    assert row["triggered_by"] == "auto"
    assert row["trigger_threshold_pct"] == 75
    assert row["model"] == "claude-sonnet-4-7"
    assert row["messages_total"] == 0
    assert row["duration_ms"] is not None
    assert row["error"] is None


def test_compact_session_loggt_error_bei_exception(setup_test_env):
    """compact_session mit nicht-existenter Session → raises + KEIN Log (Session existiert nicht)."""
    with pytest.raises(ValueError, match="nicht gefunden"):
        asyncio.run(compact_session(
            "session-existiert-nicht", model="claude-sonnet-4-7",
        ))


def _slow_compaction_setup(monkeypatch):
    from hydrahive.compaction import compactor
    from hydrahive.compaction.cut_point import CutPoint

    messages = [SimpleNamespace(role="user", content="x", token_count=10, metadata={}) for _ in range(4)]
    monkeypatch.setattr(
        compactor.sessions_db,
        "get",
        lambda _session_id: SimpleNamespace(agent_id="agent", user_id="user", project_id=None),
    )
    monkeypatch.setattr(compactor.messages_db, "list_for_session", lambda _session_id: messages)
    monkeypatch.setattr(compactor, "resolve_through_compaction", lambda history: history)
    monkeypatch.setattr(compactor, "previous_summary_text", lambda history: None)
    monkeypatch.setattr(compactor, "find_cut_point", lambda history, keep: CutPoint(kept_from_index=2))
    monkeypatch.setattr(compactor, "all_hooks", lambda: [])

    async def facts(_ctx):
        return {}

    async def slow_summary(**kwargs):
        await asyncio.sleep(1)
        return "zu spät"

    monkeypatch.setattr(compactor, "collect_facts", facts)
    monkeypatch.setattr(compactor, "serialize_for_summary", lambda messages, **kwargs: "history")
    monkeypatch.setattr(compactor, "summarize", slow_summary)
    persisted = []
    monkeypatch.setattr(compactor, "persist_compaction", lambda *args, **kwargs: persisted.append(args))
    events = []
    monkeypatch.setattr(compactor.compaction_events_db, "insert", events.append)
    return compactor, persisted, events


def test_standard_hat_kein_gesamtlimit():
    """Review 09.11.2026: erfolgreiche Compactions dauerten bis 1.025 s; ein festes Limit darunter verursacht
    Abbruch + erneutes Bezahlen. Retry-Stürme verhindert der Auto-Cooldown."""
    from hydrahive.compaction import compactor

    assert compactor.DEFAULT_COMPACTION_TIMEOUT_SECONDS is None


def test_compact_session_timeout_loggt_fehler_ohne_pointer(monkeypatch):
    compactor, persisted, events = _slow_compaction_setup(monkeypatch)

    with pytest.raises(TimeoutError):
        asyncio.run(compactor.compact_session(
            "session-1",
            model="primary-model",
            timeout_seconds=0.01,
        ))

    assert persisted == []
    assert len(events) == 1
    assert events[0].error is not None
    assert "TimeoutError" in events[0].error


def test_externe_cancellation_bleibt_cancellation_und_wird_nicht_timeout(monkeypatch):
    compactor, persisted, events = _slow_compaction_setup(monkeypatch)

    async def cancel_run():
        task = asyncio.create_task(compactor.compact_session(
            "session-1",
            model="primary-model",
            timeout_seconds=10,
        ))
        await asyncio.sleep(0.01)
        task.cancel()
        await task

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(cancel_run())

    assert persisted == []
    assert len(events) == 1
    assert events[0].error is not None
    assert "CancelledError" in events[0].error
    assert "TimeoutError" not in events[0].error
