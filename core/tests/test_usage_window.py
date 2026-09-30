"""Nutzung im Zeitfenster nach Ereigniszeit (Task a1b95d3b).

Bisher zählte das Dashboard nur Sessions, die im Zeitraum BEGONNEN haben.
Ereignisse in älteren Sessions fehlten (30.09.2026: 0,03 $ statt 223 $).
Jeder Test nutzt einen eigenen Nutzer, weil die Test-DB geteilt ist.
"""
from __future__ import annotations

import uuid

import pytest

from hydrahive.db import errors_log, init_db
from hydrahive.db import llm_calls as llm_calls_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.db.connection import db
from hydrahive.db.usage_window import top_sessions, totals

GESTERN = "2026-09-29T10:00:00.000+00:00"
HEUTE_FRUEH = "2026-09-29T22:30:00.000+00:00"   # 00:30 deutscher Zeit am 30.09.
GRENZE = "2026-09-29T22:00:00+00:00"            # 30.09. 00:00 CEST


@pytest.fixture(autouse=True)
def _db(setup_test_env):
    init_db()


@pytest.fixture
def user():
    return f"uw-{uuid.uuid4().hex[:8]}"


def _set_time(table: str, row_id: str, stamp: str) -> None:
    with db() as conn:
        conn.execute(f"UPDATE {table} SET created_at = ? WHERE id = ?", (stamp, row_id))


def _session(user: str, started: str = GESTERN) -> str:
    sid = sessions_db.create(agent_id="a-uw", user_id=user, title="uw").id
    with db() as conn:
        conn.execute("UPDATE sessions SET created_at = ? WHERE id = ?", (started, sid))
    return sid


def _llm(sid: str, user: str, stamp: str, *, cost: int = 1000, prompt: int = 100) -> None:
    cid = llm_calls_db.insert(llm_calls_db.LlmCall(
        session_id=sid, agent_id="a-uw", user_id=user, provider="anthropic", model="m-uw",
        temperature=0.7, max_tokens=100, reasoning_effort=None,
        prompt_tokens=prompt, completion_tokens=10, cache_read_tokens=5, cache_creation_tokens=2,
        stop_reason="end_turn", ttft_ms=None, total_ms=100, cost_micros=cost, turn_in_session=1,
    ))
    _set_time("llm_calls", cid, stamp)


def _tool(sid: str, user: str, stamp: str, status: str) -> None:
    mid = messages_db.append(sid, "assistant", "t").id
    tc = tools_db.create(mid, "shell_exec", {}, session_id=sid, user_id=user)
    tools_db.finish(tc.id, result="x", status=status, duration_ms=1)
    _set_time("tool_calls", tc.id, stamp)


def _err(sid: str, user: str, stamp: str, source: str) -> None:
    eid = errors_log.record(source, session_id=sid, user_id=user, message="x")
    _set_time("errors_log", eid, stamp)


def _totals(user: str, since: str = GRENZE) -> dict:
    with db() as conn:
        return totals(conn, since=since, username=user)


def test_ereignis_heute_in_session_von_gestern_zaehlt(user):
    sid = _session(user, started=GESTERN)
    _llm(sid, user, HEUTE_FRUEH, cost=12345, prompt=300)
    t = _totals(user)
    assert t["cost_micros"] == 12345
    assert t["input_tokens"] == 300 and t["output_tokens"] == 10
    assert t["cache_read_tokens"] == 5 and t["cache_creation_tokens"] == 2
    assert t["llm_calls"] == 1 and t["sessions"] == 1


def test_ereignis_vor_der_grenze_zaehlt_nicht(user):
    sid = _session(user)
    _llm(sid, user, "2026-09-29T21:59:59.999+00:00", cost=999)
    assert _totals(user)["cost_micros"] == 0


def test_tool_fehler_und_aufrufe(user):
    sid = _session(user)
    _tool(sid, user, HEUTE_FRUEH, "error")
    _tool(sid, user, HEUTE_FRUEH, "success")
    _tool(sid, user, GESTERN, "error")
    t = _totals(user)
    assert t["tool_calls"] == 2 and t["tool_errors"] == 1


def test_absturz_zaehlt_nur_als_tool_fehler(user):
    sid = _session(user)
    _tool(sid, user, HEUTE_FRUEH, "error")
    _err(sid, user, HEUTE_FRUEH, "tool.crash")
    _err(sid, user, HEUTE_FRUEH, "runner.llm_call")
    t = _totals(user)
    assert t["tool_errors"] == 1
    assert t["errors"] == 1, "tool.crash darf nicht zusätzlich in errors zählen"


def test_nur_eigene_ereignisse(user):
    other = f"{user}-x"
    _llm(_session(other), other, HEUTE_FRUEH, cost=500)
    _llm(_session(user), user, HEUTE_FRUEH, cost=7)
    assert _totals(user)["cost_micros"] == 7


def test_admin_sieht_alle(user):
    other = f"{user}-y"
    _llm(_session(other), other, HEUTE_FRUEH, cost=500)
    _llm(_session(user), user, HEUTE_FRUEH, cost=7)
    with db() as conn:
        alle = totals(conn, since=GRENZE, username=None)["cost_micros"]
    assert alle >= 507


def test_ohne_ereignisse_nullen(user):
    t = _totals(user)
    assert all(t[k] == 0 for k in ("cost_micros", "input_tokens", "llm_calls", "tool_calls",
                                   "tool_errors", "compactions", "errors", "sessions"))


def test_top_sessions_nach_kosten_im_zeitraum(user):
    alt = _session(user, started="2026-09-01T10:00:00.000+00:00")
    neu = _session(user, started=HEUTE_FRUEH)
    _llm(alt, user, "2026-09-05T10:00:00.000+00:00", cost=900_000)  # teuer, aber vor dem Zeitraum
    _llm(alt, user, HEUTE_FRUEH, cost=300)
    _llm(neu, user, HEUTE_FRUEH, cost=100)
    with db() as conn:
        rows = top_sessions(conn, since=GRENZE, username=user, limit=5)
    assert [r["session_id"] for r in rows] == [alt, neu]
    assert rows[0]["cost_micros"] == 300
    assert rows[0]["title"] == "uw" and rows[0]["agent_id"] == "a-uw"


# ── Oberfläche: /api/analytics/overview ──────────────────────────────────────

def _now_stamp() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def test_overview_zeigt_heutige_aktivitaet_einer_alten_session(client, auth_headers):
    """testuser: Session vor 10 Tagen begonnen, heute benutzt → erscheint in today und last_7d."""
    before = client.get("/api/analytics/overview", headers=auth_headers).json()
    sid = _session("testuser", started="2026-01-01T10:00:00.000+00:00")
    _llm(sid, "testuser", _now_stamp(), cost=4242)
    _tool(sid, "testuser", _now_stamp(), "error")
    after = client.get("/api/analytics/overview", headers=auth_headers).json()
    for key in ("today", "last_7d"):
        assert after[key]["cost_micros"] - before[key]["cost_micros"] == 4242, key
    assert after["today"]["tool_errors"] - before["today"]["tool_errors"] == 1
    assert sid in {r["session_id"] for r in after["top_cost_sessions"]} or \
        len(after["top_cost_sessions"]) == 5


def test_overview_top_sessions_kosten_nur_im_zeitraum(client, admin_headers):
    u = f"uw-{uuid.uuid4().hex[:8]}"
    sid = _session(u, started="2026-01-01T10:00:00.000+00:00")
    _llm(sid, u, "2026-01-02T10:00:00.000+00:00", cost=10**12)  # uralt und riesig
    _llm(sid, u, _now_stamp(), cost=10**11)                     # heute
    rows = client.get("/api/analytics/overview", headers=admin_headers).json()["top_cost_sessions"]
    mine = [r for r in rows if r["session_id"] == sid]
    assert mine and mine[0]["cost_micros"] == 10**11


def test_overview_trennt_heute_und_sieben_tage(client, auth_headers):
    """Aktivität von vor 3 Tagen zählt in last_7d, aber nicht in today."""
    from datetime import datetime, timedelta, timezone
    before = client.get("/api/analytics/overview", headers=auth_headers).json()
    sid = _session("testuser", started="2026-01-01T10:00:00.000+00:00")
    vor_drei_tagen = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(timespec="milliseconds")
    _llm(sid, "testuser", vor_drei_tagen, cost=777)
    after = client.get("/api/analytics/overview", headers=auth_headers).json()
    assert after["today"]["cost_micros"] - before["today"]["cost_micros"] == 0
    assert after["last_7d"]["cost_micros"] - before["last_7d"]["cost_micros"] == 777
