"""Bereiche Aufgabe 6 (AB6): automatisch anheften aus catalog_events (Spec 4.5)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hydrahive.catalog import auto_pin
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from tests._own_rows import only_own_rows

AGENT = "ap-agent-1"


@pytest.fixture(autouse=True)
def _sauber(setup_test_env):
    from hydrahive.db import init_db
    init_db()
    with only_own_rows("catalog_events", "sessions"):
        yield


def _sid(agent: str = AGENT) -> str:
    return sessions_db.create(agent_id=agent, user_id="admin", title="ap").id


def _run(sid: str, tool: str, n: int = 1, tage: float = 0) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(days=tage)).isoformat(timespec="milliseconds")
    with db() as conn:
        for _ in range(n):
            conn.execute("INSERT INTO catalog_events(session_id, kind, query, results, tool, created_at) "
                         "VALUES (?, 'run', '', '[]', ?, ?)", (sid, tool, ts))


def test_auto_pin_haeufigste_zuerst_max_8():
    sid = _sid()
    namen = [f"tool_{i:02d}" for i in range(12)]
    for i, n in enumerate(namen):
        _run(sid, n, n=12 - i)                       # tool_00 am häufigsten
    out = auto_pin.auto_pinned(AGENT, namen)
    assert out == namen[:8]
    assert len(out) == auto_pin.AUTO_PIN_MAX == 8


def test_auto_pin_gleichstand_nach_name():
    sid = _sid()
    _run(sid, "b_tool", 2)
    _run(sid, "a_tool", 2)
    assert auto_pin.auto_pinned(AGENT, ["a_tool", "b_tool"]) == ["a_tool", "b_tool"]


def test_auto_pin_nur_wirksame_tools():
    sid = _sid()
    _run(sid, "web_search", 5)
    _run(sid, "send_mail", 9)                        # nicht freigegeben
    _run(sid, "shell_exec", 9)                       # Kern
    _run(sid, "run_tool", 9)                         # Katalog-Werkzeug
    assert auto_pin.auto_pinned(AGENT, ["web_search", "shell_exec", "run_tool"]) == ["web_search"]


def test_auto_pin_nur_30_tage():
    sid = _sid()
    _run(sid, "alt_tool", 9, tage=31)
    _run(sid, "neu_tool", 1, tage=29)
    assert auto_pin.auto_pinned(AGENT, ["alt_tool", "neu_tool"]) == ["neu_tool"]


def test_auto_pin_nur_eigener_agent_und_nur_run():
    _run(_sid("anderer-agent"), "fremd_tool", 5)
    sid = _sid()
    with db() as conn:
        conn.execute("INSERT INTO catalog_events(session_id, kind, query, results, tool, created_at) "
                     "VALUES (?, 'search_tools', 'x', '[\"such_tool\"]', '', ?)", (sid, auto_pin._now_iso()))
    assert auto_pin.auto_pinned(AGENT, ["fremd_tool", "such_tool"]) == []


def test_auto_pin_nur_neueste_500_events():
    sid = _sid()
    _run(sid, "uralt_tool", 10)
    _run(sid, "neu_tool", 500)
    assert auto_pin.auto_pinned(AGENT, ["uralt_tool", "neu_tool"]) == ["neu_tool"]


def test_auto_pin_fehler_leer(monkeypatch, caplog):
    def kaputt(*a, **k):
        raise RuntimeError("db weg")
    monkeypatch.setattr(auto_pin, "db", kaputt)
    with caplog.at_level("WARNING"):
        assert auto_pin.auto_pinned(AGENT, ["x"]) == []
    assert "Auto-Anheften" in caplog.text


def test_auto_pin_ohne_agent_oder_tools_leer():
    assert auto_pin.auto_pinned("", ["x"]) == []
    assert auto_pin.auto_pinned(AGENT, []) == []
