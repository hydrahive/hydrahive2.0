"""Tool-Abstürze in Dashboard-Kachel und Session-Ansicht (Task ff8644b2).

Die Kachel „Heute Fehler“ zeigt errors (errors_log) + tool_errors (tool_calls).
Ein Tool-Absturz steht in beiden und darf nur EINMAL zählen (Till, Variante A).
"""
from __future__ import annotations

from pathlib import Path


from hydrahive.db import errors_log, init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.tools.base import ToolContext
from tests._tool_crash_fakes import LONG_KEY, _run

pytest_plugins = ["tests._tool_crash_fakes"]


def _shown_errors(client, headers) -> int:
    today = client.get("/api/analytics/overview", headers=headers).json()["today"]
    return today["errors"] + today["tool_errors"]


def test_dashboard_zaehlt_absturz_nur_einmal(crashing_tool, failing_tool, session_message, client, admin_headers):
    """1 Absturz + 1 normaler Fehler = +2 in der Kachel, nicht +3."""
    ctx, message_id = session_message
    before = _shown_errors(client, admin_headers)
    _run(crashing_tool, ctx, message_id, "a")
    _run(failing_tool, ctx, message_id, "b")
    assert _shown_errors(client, admin_headers) - before == 2


def test_dashboard_zaehlt_llm_fehler_weiter(session_message, client, admin_headers):
    """Andere errors_log-Quellen (z. B. runner.llm_call) zählen unverändert."""
    ctx, _ = session_message
    before = _shown_errors(client, admin_headers)
    errors_log.record(source="runner.llm_call", session_id=ctx.session_id, user_id="admin", message="x")
    assert _shown_errors(client, admin_headers) - before == 1


def test_kachel_nie_negativ_bei_nicht_admin(crashing_tool, client, auth_headers):
    """Normaler Nutzer: eigener Absturz zählt einmal, errors wird nie negativ."""
    init_db()
    s = sessions_db.create(agent_id="test-agent-crash", user_id="testuser")
    m = messages_db.append(s.id, "assistant", "tool call")
    ctx = ToolContext(session_id=s.id, agent_id="test-agent-crash", user_id="testuser", workspace=Path("/tmp"))
    before = client.get("/api/analytics/overview", headers=auth_headers).json()["today"]
    _run(crashing_tool, ctx, m.id, "u")
    after = client.get("/api/analytics/overview", headers=auth_headers).json()["today"]
    assert after["errors"] >= 0
    assert (after["errors"] + after["tool_errors"]) - (before["errors"] + before["tool_errors"]) == 1


def test_session_ansicht_zeigt_den_absturz(crashing_tool, client, auth_headers, monkeypatch):
    """Oberfläche: /api/analytics/session/{id} liefert den Absturz ohne Secret."""
    monkeypatch.setenv("OPENROUTER_API_KEY", LONG_KEY)
    init_db()
    s = sessions_db.create(agent_id="test-agent-crash", user_id="testuser")
    m = messages_db.append(s.id, "assistant", "tool call")
    ctx = ToolContext(session_id=s.id, agent_id="test-agent-crash", user_id="testuser", workspace=Path("/tmp"))
    _run(crashing_tool, ctx, m.id, "v")

    body = client.get(f"/api/analytics/session/{s.id}", headers=auth_headers).json()
    assert [e["source"] for e in body["errors"]] == ["tool.crash"]
    assert body["errors"][0]["error_type"] == "ProcessLookupError"
    assert LONG_KEY not in str(body)
