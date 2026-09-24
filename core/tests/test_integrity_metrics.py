from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.runner.integrity_metrics import summarize_integrity
from hydrahive.settings import settings


@pytest.fixture(autouse=True)
def isolated_metrics_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "sessions.db")
    init_db()


def _integrity(evidence=(), signals=()):
    return {
        "integrity": {
            "mode": "observe",
            "snapshot": {"evidence_kinds": list(evidence)},
            "signals": [
                {"kind": kind, "level": "observe", "detail": "not returned"}
                for kind in signals
            ],
        }
    }


def _session(title: str) -> str:
    init_db()
    return sessions_db.create(
        agent_id="test-agent-001", user_id="admin", title=title,
    ).id


def test_summary_counts_signals_and_evidence_deltas_without_raw_data(setup_test_env):
    sid = _session("integrity-metrics-2099")
    rows = [
        ("2099-01-01T10:00:00+00:00", (), ("completion_claim",)),
        ("2099-01-01T10:01:00+00:00", ("artifact_changed",), ()),
        ("2099-01-01T10:02:00+00:00", ("artifact_changed",), ("completion_claim",)),
        ("2099-01-01T10:03:00+00:00", ("artifact_changed", "tests_passed"), ()),
        ("2099-01-01T10:04:00+00:00", ("artifact_changed", "tests_passed"),
         ("unverified_completion_claim",)),
    ]
    for created_at, evidence, signals in rows:
        messages_db.append(
            sid, "assistant", "PRIVATE MESSAGE", metadata=_integrity(evidence, signals),
            created_at=created_at,
        )

    summary = summarize_integrity(
        hours=2, now=datetime(2099, 1, 1, 11, tzinfo=timezone.utc),
    )

    assert summary["messages_observed"] == 5
    assert summary["sessions_observed"] == 1
    assert summary["signal_counts"] == {
        "completion_claim": 2, "unverified_completion_claim": 1,
    }
    assert summary["evidence_counts"] == {"artifact_changed": 1, "tests_passed": 1}
    assert summary["completion_claims"] == 2
    assert summary["unverified_completion_claims"] == 1
    assert summary["unverified_rate"] == 0.5
    assert "PRIVATE MESSAGE" not in repr(summary)
    assert sid not in repr(summary)
    assert "admin" not in repr(summary)


def test_summary_skips_malformed_metadata_and_reports_it(setup_test_env):
    sid = _session("integrity-malformed-2097")
    message = messages_db.append(
        sid, "assistant", "private", metadata=_integrity(),
        created_at="2097-01-01T10:00:00+00:00",
    )
    with db() as conn:
        conn.execute(
            "UPDATE messages SET metadata=? WHERE id=?",
            ('{"integrity": broken', message.id),
        )

    summary = summarize_integrity(
        hours=2, now=datetime(2097, 1, 1, 11, tzinfo=timezone.utc),
    )

    assert summary["messages_observed"] == 0
    assert summary["malformed_metadata"] == 1


def test_summary_caps_candidate_rows_and_marks_truncated(setup_test_env):
    sid = _session("integrity-limit-2098")
    for minute in range(3):
        messages_db.append(
            sid, "assistant", "private", metadata=_integrity(),
            created_at=f"2098-01-01T10:0{minute}:00+00:00",
        )

    summary = summarize_integrity(
        hours=2, now=datetime(2098, 1, 1, 11, tzinfo=timezone.utc), max_rows=2,
    )

    assert summary["messages_observed"] == 2
    assert summary["truncated"] is True
    assert summary["candidate_rows"] == 3
