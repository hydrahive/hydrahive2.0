"""Tests für session_metrics-VIEW + Wrapper (Token-Audit #129, PR 5)."""
from __future__ import annotations

import pytest

from hydrahive.db import compaction_events as compaction_events_db
from hydrahive.db import errors_log
from hydrahive.db import init_db
from hydrahive.db import llm_calls as llm_calls_db
from hydrahive.db import messages as messages_db
from hydrahive.db import session_metrics
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db


@pytest.fixture(autouse=True)
def _db(setup_test_env):
    init_db()


def _make_session(*, user_id: str = "testuser", agent_id: str = "test-agent-001") -> str:
    return sessions_db.create(agent_id=agent_id, user_id=user_id, title="metrics-test").id


def _llm(sid: str, *, prompt: int, completion: int, cache_read: int = 0,
         cache_creation: int = 0, cost: int = 100, ms: int = 500) -> None:
    llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=sid, agent_id="test-agent-001", user_id="testuser",
        provider="anthropic", model="claude-sonnet-4-7",
        temperature=0.7, max_tokens=4096, reasoning_effort=None,
        prompt_tokens=prompt, completion_tokens=completion,
        cache_read_tokens=cache_read, cache_creation_tokens=cache_creation,
        stop_reason="end_turn", ttft_ms=None, total_ms=ms,
        cost_micros=cost, turn_in_session=1,
    ))


def test_view_leere_session_alle_nullen():
    sid = _make_session()
    m = session_metrics.for_session(sid)
    assert m is not None
    assert m["llm_calls"] == 0
    assert m["input_tokens"] == 0
    assert m["cost_micros"] == 0
    assert m["tool_calls"] == 0
    assert m["compactions"] == 0
    assert m["errors"] == 0


def test_view_aggregiert_llm_calls():
    sid = _make_session()
    _llm(sid, prompt=1000, completion=200, cache_read=500, cost=100, ms=400)
    _llm(sid, prompt=2000, completion=300, cache_read=800, cost=200, ms=600)
    m = session_metrics.for_session(sid)
    assert m is not None
    assert m["llm_calls"] == 2
    assert m["input_tokens"] == 3000
    assert m["output_tokens"] == 500
    assert m["cache_read_tokens"] == 1300
    assert m["cost_micros"] == 300
    assert m["total_llm_ms"] == 1000


def test_view_aggregiert_tool_calls_und_errors():
    sid = _make_session()
    mid = messages_db.append(sid, "assistant", "tools").id
    tc1 = tools_db.create(mid, "shell_exec", {"cmd": "ls"}, session_id=sid)
    tools_db.finish(tc1.id, result="ok", status="success", duration_ms=100)
    tc2 = tools_db.create(mid, "fetch_url", {"u": "x"}, session_id=sid)
    tools_db.finish(tc2.id, result="boom", status="error", duration_ms=50,
                    error_type="TimeoutError", error_message="boom")
    tc3 = tools_db.create(mid, "file_read", {}, session_id=sid)
    tools_db.finish(tc3.id, result="big", status="success", duration_ms=20)
    tools_db.mark_truncated(tc3.id, 2000)

    m = session_metrics.for_session(sid)
    assert m is not None
    assert m["tool_calls"] == 3
    assert m["tool_successes"] == 2
    assert m["tool_errors"] == 1
    assert m["tool_truncates"] == 1
    assert m["tool_total_ms"] == 170


def test_view_zaehlt_compactions_und_errors_log():
    sid = _make_session()
    compaction_events_db.insert(compaction_events_db.CompactionEvent(
        session_id=sid, agent_id="test-agent-001", user_id="testuser",
        triggered_by="auto", trigger_threshold_pct=75,
        model="claude-sonnet-4-7", source="default",
        instructions=None, tool_result_limit=None,
        skipped=False, skip_reason=None, skip_reason_params=None,
        messages_total=20, messages_visible_before=20,
        messages_to_summarize=10, messages_kept=10,
        tokens_before=100_000, tokens_after_estimate=20_000,
        cut_kept_from_index=10, cut_is_split_turn=False, cut_turn_prefix_count=0,
        summary_chars=1000, summary_tokens_estimate=250,
        facts_count=2, files_extracted_count=1,
        compaction_message_id="mc_x", had_previous_summary=False,
        duration_ms=2000, error=None,
    ))
    compaction_events_db.insert(compaction_events_db.CompactionEvent(
        session_id=sid, agent_id=None, user_id=None,
        triggered_by="auto", trigger_threshold_pct=None,
        model=None, source=None, instructions=None, tool_result_limit=None,
        skipped=True, skip_reason="too_short", skip_reason_params=None,
        messages_total=None, messages_visible_before=None,
        messages_to_summarize=None, messages_kept=None,
        tokens_before=None, tokens_after_estimate=None,
        cut_kept_from_index=None, cut_is_split_turn=None, cut_turn_prefix_count=None,
        summary_chars=None, summary_tokens_estimate=None,
        facts_count=None, files_extracted_count=None,
        compaction_message_id=None, had_previous_summary=None,
        duration_ms=5, error=None,
    ))
    errors_log.record(source="test", session_id=sid, message="x")
    errors_log.record(source="test", session_id=sid, message="y")

    m = session_metrics.for_session(sid)
    assert m is not None
    assert m["compactions"] == 2
    assert m["compactions_skipped"] == 1
    assert m["errors"] == 2


def test_for_agent_listet_alle_sessions_des_agents():
    # Eigener Agent damit kein Mischmasch mit anderen Tests
    aid = "agent-listing-test"
    s1 = sessions_db.create(agent_id=aid, user_id="testuser", title="x1").id
    s2 = sessions_db.create(agent_id=aid, user_id="testuser", title="x2").id
    rows = session_metrics.for_agent(aid)
    sids = {r["session_id"] for r in rows}
    assert sids == {s1, s2}
    # Andere Agents tauchen nicht auf
    other_sids = session_metrics.for_agent("test-agent-001")
    assert s1 not in {r["session_id"] for r in other_sids}


def test_top_cost_filter_und_order():
    # Eigener Agent damit der Top-Cost-Filter nicht mit anderen Test-Sessions
    # kollidiert (test_llm_calls_logging schreibt z.B. cost_micros=652)
    aid = "agent-topcost-test"
    s_cheap = sessions_db.create(agent_id=aid, user_id="testuser", title="c").id
    s_mid = sessions_db.create(agent_id=aid, user_id="testuser", title="m").id
    s_pricey = sessions_db.create(agent_id=aid, user_id="testuser", title="p").id
    for sid, cost in [(s_cheap, 50), (s_mid, 500), (s_pricey, 5000)]:
        llm_calls_db.insert(llm_calls_db.LlmCall(
            session_id=sid, agent_id=aid, user_id="testuser",
            provider="anthropic", model="claude-sonnet-4-7",
            temperature=0.7, max_tokens=4096, reasoning_effort=None,
            prompt_tokens=100, completion_tokens=10,
            cache_read_tokens=0, cache_creation_tokens=0,
            stop_reason="end_turn", ttft_ms=None, total_ms=100,
            cost_micros=cost, turn_in_session=1,
        ))

    top = session_metrics.top_cost(limit=2, agent_id=aid)
    assert top[0]["session_id"] == s_pricey
    assert top[0]["cost_micros"] == 5000
    assert top[1]["session_id"] == s_mid
    assert len(top) == 2


def test_totals_for_agent_aggregiert_alle_sessions():
    aid = "agg-test-agent"
    s1 = sessions_db.create(agent_id=aid, user_id="testuser", title="a1").id
    s2 = sessions_db.create(agent_id=aid, user_id="testuser", title="a2").id

    llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=s1, agent_id=aid, user_id="testuser",
        provider="anthropic", model="claude-sonnet-4-7",
        temperature=0.7, max_tokens=4096, reasoning_effort=None,
        prompt_tokens=1000, completion_tokens=100,
        cache_read_tokens=0, cache_creation_tokens=0,
        stop_reason="end_turn", ttft_ms=None, total_ms=300,
        cost_micros=300, turn_in_session=1,
    ))
    llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=s2, agent_id=aid, user_id="testuser",
        provider="anthropic", model="claude-sonnet-4-7",
        temperature=0.7, max_tokens=4096, reasoning_effort=None,
        prompt_tokens=2000, completion_tokens=200,
        cache_read_tokens=500, cache_creation_tokens=0,
        stop_reason="end_turn", ttft_ms=None, total_ms=600,
        cost_micros=700, turn_in_session=1,
    ))

    totals = session_metrics.totals_for_agent(aid)
    assert totals["sessions"] == 2
    assert totals["llm_calls"] == 2
    assert totals["input_tokens"] == 3000
    assert totals["output_tokens"] == 300
    assert totals["cache_read_tokens"] == 500
    assert totals["cost_micros"] == 1000


def test_for_session_unbekannt_returnt_none():
    assert session_metrics.for_session("session-existiert-nicht") is None
