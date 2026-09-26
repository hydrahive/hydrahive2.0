"""Lange Sessions dürfen den Chat nicht mehr mit dem kompletten Verlauf fluten.

`list_for_session(limit=...)` liefert bewusst die ÄLTESTEN Nachrichten (Export,
Migration). Der Chat braucht das Gegenteil: die letzten N in chronologischer
Reihenfolge, damit ein Reload klein bleibt.
"""
from __future__ import annotations

from hydrahive.db import init_db, messages, sessions
from hydrahive.settings import settings


def _session(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "sessions.db")
    init_db()
    s = sessions.create(agent_id="a1", user_id="u1")
    for i in range(25):
        messages.append(s.id, "user", f"m{i:02d}")
    return s


def test_tail_returns_newest_messages_in_chronological_order(tmp_path, monkeypatch):
    s = _session(tmp_path, monkeypatch)

    tail = messages.list_tail_for_session(s.id, limit=5)

    assert [m.content for m in tail] == ["m20", "m21", "m22", "m23", "m24"]


def test_tail_without_limit_returns_everything(tmp_path, monkeypatch):
    s = _session(tmp_path, monkeypatch)

    assert len(messages.list_tail_for_session(s.id, limit=None)) == 25
    assert len(messages.list_tail_for_session(s.id, limit=999)) == 25


def test_tail_differs_from_head_limit(tmp_path, monkeypatch):
    """Absicherung gegen Verwechslung: LIMIT ohne DESC liefert die ältesten."""
    s = _session(tmp_path, monkeypatch)

    head = messages.list_for_session(s.id, limit=3)
    tail = messages.list_tail_for_session(s.id, limit=3)

    assert [m.content for m in head] == ["m00", "m01", "m02"]
    assert [m.content for m in tail] == ["m22", "m23", "m24"]
