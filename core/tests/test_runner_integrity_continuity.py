from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner.integrity_continuity import (
    is_direct_continuation,
    load_continuation_evidence,
)

_AGENT_ID = "test-agent-001"


@pytest.mark.parametrize("text", [
    "weiter",
    "Ok, dann der Reihe nach weiter.",
    "Ok, machen wir das alles noch fertig und dann die Agenten.",
    "Bitte weitermachen",
    "continue",
    "Please proceed",
    "Auf welchem Stand sind wir?",
    "Ok, auf welchem Stand sind wir?",
    "Wie ist der aktuelle Status?",
])
def test_direct_continuation_accepts_conservative_phrases(text):
    assert is_direct_continuation(text) is True


@pytest.mark.parametrize("text", [
    "Implementiere eine weitere Funktion",
    "Nicht weiter, bitte stoppen",
    "Machen wir das nicht fertig, bitte stoppen",
    "Mach die neue Agentenverwaltung fertig",
    "Continue implementing OAuth with a new database",
    "Was ist der Status von Bestellung 123?",
    "Schreibe eine Statusseite",
    "",
])
def test_direct_continuation_rejects_new_or_ambiguous_work(text):
    assert is_direct_continuation(text) is False


def _session(title: str):
    return sessions_db.create(agent_id=_AGENT_ID, user_id="admin", title=title)


def _metadata(evidence):
    return {
        "integrity": {
            "mode": "observe",
            "snapshot": {"evidence_kinds": list(evidence)},
            "signals": [],
        }
    }


def test_loads_only_latest_same_session_evidence_for_continuation(setup_test_env):
    init_db()
    own = _session("continuity-own")
    other = _session("continuity-other")
    messages_db.append(
        own.id, "assistant", "private", metadata=_metadata(("artifact_changed", "tests_passed")),
        created_at="2099-01-01T10:00:00+00:00",
    )
    messages_db.append(
        other.id, "assistant", "private", metadata=_metadata(("commit_created",)),
        created_at="2099-01-01T10:05:00+00:00",
    )

    evidence = load_continuation_evidence(
        own.id, "weiter", now=datetime(2099, 1, 1, 11, tzinfo=timezone.utc),
    )

    assert evidence == frozenset({"artifact_changed", "tests_passed"})


def test_does_not_query_history_for_fresh_work(setup_test_env, monkeypatch):
    init_db()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("history must not be queried")

    monkeypatch.setattr("hydrahive.runner.integrity_continuity.db", fail_if_called)

    assert load_continuation_evidence("unused", "Implementiere OAuth") == frozenset()


def test_rejects_expired_unknown_and_malformed_evidence(setup_test_env):
    init_db()
    expired = _session("continuity-expired")
    unknown = _session("continuity-unknown")
    malformed = _session("continuity-malformed")
    messages_db.append(
        expired.id, "assistant", "private", metadata=_metadata(("tests_passed",)),
        created_at="2099-01-01T10:00:00+00:00",
    )
    messages_db.append(
        unknown.id, "assistant", "private",
        metadata=_metadata(("artifact_changed", "private_evidence")),
        created_at="2099-01-03T10:00:00+00:00",
    )
    messages_db.append(
        malformed.id, "assistant", "private", metadata={"integrity": "bad"},
        created_at="2099-01-03T10:00:00+00:00",
    )
    now = datetime(2099, 1, 3, 11, tzinfo=timezone.utc)

    assert load_continuation_evidence(expired.id, "weiter", now=now) == frozenset()
    assert load_continuation_evidence(unknown.id, "weiter", now=now) == frozenset({"artifact_changed"})
    assert load_continuation_evidence(malformed.id, "weiter", now=now) == frozenset()


def test_latest_empty_snapshot_does_not_revive_older_evidence(setup_test_env):
    init_db()
    session = _session("continuity-latest")
    messages_db.append(
        session.id, "assistant", "private", metadata=_metadata(("tests_passed",)),
        created_at="2099-01-01T10:00:00+00:00",
    )
    messages_db.append(
        session.id, "assistant", "private", metadata=_metadata(()),
        created_at="2099-01-01T10:05:00+00:00",
    )

    evidence = load_continuation_evidence(
        session.id, "weiter", now=datetime(2099, 1, 1, 11, tzinfo=timezone.utc),
    )

    assert evidence == frozenset()
