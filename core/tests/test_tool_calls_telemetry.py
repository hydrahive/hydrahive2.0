"""Tests für tool_calls-Telemetrie (Token-Audit #129, PR 3).

Deckt: create-mit-Kontext, finish-mit-Fehler-Details, mark_truncated,
list_for_session-Query, _extract_error_type-Heuristik.
"""
from __future__ import annotations

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.runner.dispatcher import _extract_error_type


def _seed() -> tuple[str, str]:
    """Returns (session_id, message_id) — beide existieren."""
    init_db()
    s = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="tool-tel")
    m = messages_db.append(s.id, "assistant", "Tool-Aufruf")
    return s.id, m.id


def test_create_persistiert_kontext_und_args_size(setup_test_env):
    session_id, message_id = _seed()
    args = {"path": "/tmp/foo.txt", "content": "hallo welt"}
    tc = tools_db.create(
        message_id, "file_write", args,
        session_id=session_id, agent_id="test-agent-001", user_id="testuser",
        tool_use_id="toolu_abc123", iteration=3,
    )
    assert tc.session_id == session_id
    assert tc.agent_id == "test-agent-001"
    assert tc.user_id == "testuser"
    assert tc.tool_use_id == "toolu_abc123"
    assert tc.iteration == 3
    assert tc.arguments_size_bytes is not None and tc.arguments_size_bytes > 0

    fetched = tools_db.get(tc.id)
    assert fetched is not None
    assert fetched.session_id == session_id
    assert fetched.arguments_size_bytes == tc.arguments_size_bytes


def test_finish_setzt_result_size_und_error_felder(setup_test_env):
    _, message_id = _seed()
    tc = tools_db.create(message_id, "shell_exec", {"cmd": "ls"})

    tools_db.finish(
        tc.id, result={"output": "datei1\ndatei2\n"},
        status="success", duration_ms=42,
    )
    refetched = tools_db.get(tc.id)
    assert refetched is not None
    assert refetched.status == "success"
    assert refetched.duration_ms == 42
    assert refetched.result_size_bytes is not None and refetched.result_size_bytes > 0
    assert refetched.error_type is None
    assert refetched.error_message is None


def test_finish_mit_fehler_speichert_typ_und_msg(setup_test_env):
    _, message_id = _seed()
    tc = tools_db.create(message_id, "broken_tool", {})
    tools_db.finish(
        tc.id, result={"error": "boom"},
        status="error", duration_ms=10,
        error_type="ValueError",
        error_message="Tool-Crash: ValueError: boom",
    )
    refetched = tools_db.get(tc.id)
    assert refetched is not None
    assert refetched.status == "error"
    assert refetched.error_type == "ValueError"
    assert refetched.error_message == "Tool-Crash: ValueError: boom"


def test_mark_truncated_setzt_flag_und_limit(setup_test_env):
    _, message_id = _seed()
    tc = tools_db.create(message_id, "file_read", {"path": "/big.log"})
    tools_db.mark_truncated(tc.id, 2000)
    refetched = tools_db.get(tc.id)
    assert refetched is not None
    assert refetched.result_truncated is True
    assert refetched.truncate_limit_chars == 2000


def test_list_for_session_filtert_korrekt(setup_test_env):
    session_id, message_id = _seed()
    tools_db.create(message_id, "tool_a", {}, session_id=session_id)
    tools_db.create(message_id, "tool_b", {}, session_id=session_id)
    # andere Session — darf nicht auftauchen
    s2 = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="other")
    m2 = messages_db.append(s2.id, "assistant", "x")
    tools_db.create(m2.id, "tool_other", {}, session_id=s2.id)

    rows = tools_db.list_for_session(session_id)
    names = [r.tool_name for r in rows]
    assert names == ["tool_a", "tool_b"]


def test_extract_error_type_heuristik():
    assert _extract_error_type("Tool-Crash: ValueError: invalid") == "ValueError"
    assert _extract_error_type("MCP-Crash: TimeoutError: 30s") == "TimeoutError"
    assert _extract_error_type("Tool-Crash: KeyError") == "KeyError"
    assert _extract_error_type("Vom Benutzer abgelehnt") is None
    assert _extract_error_type(None) is None
    assert _extract_error_type("") is None
