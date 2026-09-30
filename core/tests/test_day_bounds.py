"""Tagesgrenzen fürs Dashboard nach deutscher Zeit (Task a1b95d3b).

Till 30.09.2026: „heute“ beginnt um Mitternacht in Europe/Berlin.
Die DB speichert UTC (…+00:00, alte messages auch …Z); die Grenze muss
deshalb als UTC-Zeitstempel im selben Textformat kommen.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hydrahive.api.routes._dashboard_helpers import today_start_iso, week_start_iso


def _utc(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize(("now", "expected"), [
    ("2026-09-30T20:00:00", "2026-09-29T22:00:00+00:00"),  # Sommerzeit: 00:00 CEST = 22:00 UTC
    ("2026-09-29T22:30:00", "2026-09-29T22:00:00+00:00"),  # 00:30 deutsch, UTC noch Vortag
    ("2026-09-29T21:30:00", "2026-09-28T22:00:00+00:00"),  # 23:30 deutsch → noch der 29.
    ("2026-12-15T12:00:00", "2026-12-14T23:00:00+00:00"),  # Winterzeit: 00:00 CET = 23:00 UTC
])
def test_today_start_ist_deutsche_mitternacht_in_utc(now, expected):
    assert today_start_iso(_utc(now)) == expected


def test_week_start_sieben_deutsche_tage_zurueck_auch_ueber_zeitumstellung():
    # 29.10.2026: Winterzeit seit 25.10. → heute 00:00 CET = 28.10. 23:00 UTC,
    # 7 Tage vorher 22.10. 00:00 CEST = 21.10. 22:00 UTC
    now = _utc("2026-10-29T12:00:00")
    assert today_start_iso(now) == "2026-10-28T23:00:00+00:00"
    assert week_start_iso(now) == "2026-10-21T22:00:00+00:00"


def test_ohne_argument_gilt_jetzt():
    start = datetime.fromisoformat(today_start_iso())
    now = datetime.now(timezone.utc)
    assert start <= now
    assert (now - start).total_seconds() < 25 * 3600


@pytest.mark.parametrize("stamp", ["2026-09-29T22:00:00.001+00:00", "2026-09-29T22:00:00.001Z"])
def test_textvergleich_passt_zu_beiden_speicherformaten(stamp):
    grenze = today_start_iso(_utc("2026-09-30T08:00:00"))
    assert stamp >= grenze
    assert "2026-09-29T21:59:59.999+00:00" < grenze
    assert "2026-09-29T21:59:59.999Z" < grenze


# ── Oberfläche: /api/dashboard nutzt dieselbe deutsche Tagesgrenze ───────────

def test_dashboard_tool_aufruf_kurz_nach_deutscher_mitternacht_zaehlt(client, admin_headers, monkeypatch):
    """Tool-Aufruf um 00:30 deutscher Zeit zählt zu „heute“, einer um 23:30 am Vortag nicht.
    Vorher (UTC-Grenze) war es genau umgekehrt."""
    from hydrahive.api.routes import dashboard as dashboard_route
    from hydrahive.db import init_db
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import tools as tools_db
    from hydrahive.db.connection import db

    init_db()
    fixed_now = _utc("2026-09-30T08:00:00")
    monkeypatch.setattr(dashboard_route, "today_start_iso", lambda: today_start_iso(fixed_now))

    def _count() -> int:
        return client.get("/api/dashboard", headers=admin_headers).json()["stats"]["tool_calls_today"]

    before = _count()
    sid = sessions_db.create(agent_id="a-db", user_id="admin", title="db").id
    mid = messages_db.append(sid, "assistant", "x").id
    for stamp in ("2026-09-29T22:30:00.000+00:00", "2026-09-29T21:30:00.000+00:00"):
        tc = tools_db.create(mid, "shell_exec", {}, session_id=sid, user_id="admin")
        with db() as conn:
            conn.execute("UPDATE tool_calls SET created_at = ? WHERE id = ?", (stamp, tc.id))
    assert _count() - before == 1
