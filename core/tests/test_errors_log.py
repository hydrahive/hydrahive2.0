"""Tests für errors_log — record, capture-CM, read-paths (Token-Audit #129, PR 4)."""
from __future__ import annotations

import pytest

from hydrahive.db import errors_log
from hydrahive.db import init_db


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    init_db()


def test_record_ohne_exception_persistiert():
    eid = errors_log.record(
        source="test.manual",
        severity="warning",
        message="manual warning",
        error_type="ManualWarning",
        context={"detail": "synthetic"},
    )
    assert eid is not None and eid.startswith("err_")
    rows = errors_log.recent(limit=10)
    assert any(r["id"] == eid for r in rows)
    row = next(r for r in rows if r["id"] == eid)
    assert row["source"] == "test.manual"
    assert row["severity"] == "warning"
    assert row["error_type"] == "ManualWarning"
    assert row["error_message"] == "manual warning"
    assert row["traceback"] is None  # ohne exc kein TB


def test_record_mit_exception_speichert_typ_und_tb():
    try:
        raise ValueError("boom-test-payload")
    except ValueError as e:
        eid = errors_log.record(
            source="test.exc",
            exc=e,
            session_id="sess-1",
            agent_id="agent-1",
            user_id="user-1",
        )
    assert eid is not None
    rows = errors_log.recent(limit=5)
    row = next(r for r in rows if r["id"] == eid)
    assert row["error_type"] == "ValueError"
    assert row["error_message"] == "boom-test-payload"
    assert row["traceback"] is not None
    assert "boom-test-payload" in row["traceback"]
    assert row["session_id"] == "sess-1"
    assert row["agent_id"] == "agent-1"
    assert row["user_id"] == "user-1"


def test_capture_logged_und_reraisst_default():
    with pytest.raises(RuntimeError, match="from-capture"):
        with errors_log.capture(source="test.capture", session_id="s-cap"):
            raise RuntimeError("from-capture")
    rows = errors_log.for_session("s-cap")
    assert len(rows) == 1
    assert rows[0]["error_type"] == "RuntimeError"
    assert rows[0]["error_message"] == "from-capture"
    assert rows[0]["source"] == "test.capture"


def test_capture_reraise_false_schluckt_exception():
    # Kein pytest.raises — Exception soll geschluckt werden
    with errors_log.capture(source="test.capture.noreraise",
                            session_id="s-bg", reraise=False):
        raise KeyError("background-task-error")
    rows = errors_log.for_session("s-bg")
    assert len(rows) == 1
    assert rows[0]["error_type"] == "KeyError"
    # KeyError("...") stringified ist '"..."' inkl. Anführungszeichen — daher 'in'
    assert "background-task-error" in rows[0]["error_message"]


def test_recent_filter_severity():
    errors_log.record(source="test.filter", severity="error", message="e1")
    errors_log.record(source="test.filter", severity="warning", message="w1")
    errors_log.record(source="test.filter", severity="critical", message="c1")
    crits = errors_log.recent(limit=20, severity="critical")
    assert all(r["severity"] == "critical" for r in crits)
    assert any(r["error_message"] == "c1" for r in crits)


def test_for_session_filtert_korrekt():
    errors_log.record(source="test.s", session_id="sX", message="x1")
    errors_log.record(source="test.s", session_id="sX", message="x2")
    errors_log.record(source="test.s", session_id="sY", message="y1")
    xs = errors_log.for_session("sX")
    assert len(xs) == 2
    assert {r["error_message"] for r in xs} == {"x1", "x2"}


def test_context_persistiert_als_json():
    import json as _json
    eid = errors_log.record(
        source="test.ctx",
        message="ctx-check",
        context={"model": "claude-sonnet-4-7", "iteration": 5, "nested": {"k": "v"}},
    )
    row = next(r for r in errors_log.recent(limit=10) if r["id"] == eid)
    ctx = _json.loads(row["context"])
    assert ctx["model"] == "claude-sonnet-4-7"
    assert ctx["iteration"] == 5
    assert ctx["nested"] == {"k": "v"}
