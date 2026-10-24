"""Werkzeug error_report_prepare (docs/plans/help-error-report.md): bereitet vor, sendet NIE.

Seite kommt vom Server (zuletzt im Hilfe-Fenster gemeldet), nicht vom Modell. Nur im Hilfe-Agenten.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clean(setup_test_env, monkeypatch):
    from hydrahive.db import init_db
    from hydrahive.helpdesk import _report
    init_db()
    _report._DRAFTS.clear()
    _report._PAGES.clear()
    yield
    _report._DRAFTS.clear()
    _report._PAGES.clear()


def _ctx(user="tooluser", sid="hs1"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id=sid, agent_id="a", user_id=user, workspace=Path("/tmp"))


def _run(args, ctx):
    from hydrahive.tools import error_report_prepare
    return asyncio.run(error_report_prepare.TOOL.execute(args, ctx))


def test_bereitet_vor_und_sendet_nicht(monkeypatch):
    from hydrahive.communication.mail import _transport
    from hydrahive.helpdesk import _report
    calls = []
    monkeypatch.setattr(_transport, "send_message", lambda cfg, msg: calls.append(msg))
    _report.remember_page("hs1", "/mailbox")
    r = _run({"description": "Senden geht nicht"}, _ctx())
    assert r.success and calls == []
    rid = r.output["report_id"]
    d = _report.get("tooluser", rid)
    assert "Seite: /mailbox" in d["body"] and "Senden geht nicht" in d["body"]
    assert r.output["to"] == "issue@hydrahive.org" and r.output["errors_found"] == 0
    assert "Senden" in r.output["next"], "Hinweis: Nutzer muss im Fenster auf Senden klicken"


def test_seite_nicht_vom_modell(monkeypatch):
    from hydrahive.helpdesk import _report
    _report.remember_page("hs1", "/chat")
    r = _run({"description": "x", "path": "/admin/geheim"}, _ctx())
    assert "Seite: /chat" in _report.get("tooluser", r.output["report_id"])["body"]


def test_seite_je_sitzung():
    from hydrahive.helpdesk import _report
    _report.remember_page("hs1", "/mailbox")
    r = _run({"description": "x"}, _ctx(sid="andere"))
    assert "Seite: unbekannt" in _report.get("tooluser", r.output["report_id"])["body"]


def test_ohne_beschreibung_abgelehnt():
    assert not _run({}, _ctx()).success
    assert not _run({"description": "   "}, _ctx()).success


def test_schalter_aus(monkeypatch):
    from hydrahive.helpdesk import _report
    monkeypatch.setattr(_report, "enabled", lambda: False)
    r = _run({"description": "x"}, _ctx())
    assert not r.success and "ausgeschaltet" in r.error


def test_nur_im_hilfe_agenten():
    from hydrahive.agents._defaults import _BASE_TOOLS
    from hydrahive.helpdesk._agent import HELP_TOOLS
    assert "error_report_prepare" in HELP_TOOLS
    assert all("error_report_prepare" not in v for v in _BASE_TOOLS.values())
    from hydrahive.tools import REGISTRY
    assert REGISTRY["error_report_prepare"].category == "help"


def test_prompt_erklaert_fehler_melden():
    from hydrahive.helpdesk._agent import SYSTEM_PROMPT
    assert "error_report_prepare" in SYSTEM_PROMPT and "Senden" in SYSTEM_PROMPT


def test_route_merkt_seite(client, auth_headers, monkeypatch):
    """POST /api/helpdesk/messages merkt die bereinigte Seite für das Werkzeug (je Hilfe-Sitzung)."""
    from hydrahive.api.routes import helpdesk as route
    from hydrahive.helpdesk import _report
    monkeypatch.setattr(route, "get_or_create_help_agent",
                        lambda user: {"model_missing": False, "session_id": "hs-route", "agent_id": "a"})

    async def fake_stream(sid, text, extra_system=None):
        return {"ok": True}
    monkeypatch.setattr(route, "run_and_stream", fake_stream)
    r = client.post("/api/helpdesk/messages", json={"session_id": "hs-route", "text": "hi", "path": "/mailbox?x=1"},
                    headers=auth_headers)
    assert r.status_code == 200 and _report.page_for("hs-route") == "/mailbox"
