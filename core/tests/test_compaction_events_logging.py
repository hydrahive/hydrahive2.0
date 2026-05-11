"""Tests für compaction_events — DB-Roundtrip + compact_session-Hook (Token-Audit #129)."""
from __future__ import annotations

import asyncio

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
