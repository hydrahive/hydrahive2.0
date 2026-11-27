"""Katalog Etappe 6, Aufgabe 7: Messung gesucht / gefunden / benutzt je Sitzung (Spec V7, K8).

Erfasst werden find_tools, find_skills (Suche) und run_tool (erfolgreiche Benutzung). „Gesucht, nichts benutzt“ heißt: Nach
einer Tool-Suche wurde keiner der Treffer später in derselben Sitzung per run_tool erfolgreich benutzt.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from hydrahive.tools.base import ToolContext, ToolResult
from tests._own_rows import only_own_rows


@pytest.fixture(autouse=True)
def _sauber(setup_test_env):
    from hydrahive.db import init_db
    init_db()
    with only_own_rows("catalog_events"):
        yield


@pytest.fixture
def sitzung(client):
    from hydrahive.db import sessions as sessions_db
    made: list[str] = []

    def make(user: str = "testuser") -> str:
        s = sessions_db.create(agent_id="test-agent-user" if user == "testuser" else "test-agent-001",
                               user_id=user, title="metrik")
        made.append(s.id)
        return s.id

    yield make


def _ctx(tmp_path: Path, sid: str) -> ToolContext:
    return ToolContext(session_id=sid, agent_id="a1", user_id="testuser", workspace=tmp_path)


def _find_tools(tmp_path, sid, query, allowed, monkeypatch, **extra):
    from hydrahive.catalog import _store
    from hydrahive.tools import find_tools
    _store.reset_store()
    monkeypatch.setattr(find_tools, "_allowed_for", lambda ctx: set(allowed))
    return asyncio.run(find_tools.TOOL.execute({"query": query, **extra}, _ctx(tmp_path, sid)))


def _run_tool(tmp_path, sid, inner, args, monkeypatch, *, ok=True):
    """Ein run_tool-Aufruf durch den echten Runner-Pfad (process_tool_uses); nur die Ausführung ist ersetzt."""
    from hydrahive.runner import _runner_tools

    async def fake_exec(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        return (ToolResult.ok("lief") if ok else ToolResult.fail("kaputt")), "rec1", 1

    monkeypatch.setattr(_runner_tools, "execute_tool", fake_exec)
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    monkeypatch.setattr(_runner_tools, "remember_catalog_tool", lambda *a, **k: None)
    tu = {"id": "c1", "name": "run_tool", "input": {"name": inner, "args": args}}

    async def go():
        async for _ in _runner_tools.process_tool_uses(
                [tu], ctx=_ctx(tmp_path, sid), allowed_tools=["run_tool", "generate_image", "web_search", "send_mail"],
                parent_message_id="m1", require_confirm=False, tool_result_max_chars=10000):
            pass
    asyncio.run(go())


def test_migration_069_tabelle_da():
    from hydrahive.db.connection import db
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(catalog_events)")}
        idx = {r["name"] for r in conn.execute("PRAGMA index_list(catalog_events)")}
    assert {"session_id", "kind", "query", "results", "tool", "created_at"} <= cols
    assert any("session" in n for n in idx)


def test_metrik_sucht_findet_benutzt(sitzung, tmp_path, monkeypatch):
    from hydrahive.catalog import metrics
    sid = sitzung()
    res = _find_tools(tmp_path, sid, "Bild erzeugen", {"generate_image", "web_search", "send_mail"}, monkeypatch)
    assert res.success
    gefunden = [r["name"] for r in res.output["results"]]
    assert gefunden[0] == "generate_image"
    _run_tool(tmp_path, sid, "generate_image", {"prompt": "eine Hydra"}, monkeypatch)
    s = metrics.summary(sid)
    assert s["session_id"] == sid
    assert s["searches"] == 1 and s["tool_searches"] == 1
    assert s["found"] == gefunden
    assert s["used"] == ["generate_image"]
    assert s["searches_unused"] == 0
    erste = s["events"][0]
    assert erste["kind"] == "search_tools" and erste["query"] == "Bild erzeugen" and erste["used"] is True
    assert erste["results"] == gefunden


def test_gesucht_nichts_benutzt_markiert(sitzung, tmp_path, monkeypatch):
    from hydrahive.catalog import metrics
    sid = sitzung()
    _find_tools(tmp_path, sid, "Bild erzeugen", {"generate_image", "web_search"}, monkeypatch)
    _find_tools(tmp_path, sid, "im Web suchen", {"generate_image", "web_search"}, monkeypatch)
    _run_tool(tmp_path, sid, "web_search", {"query": "x"}, monkeypatch)       # nur die zweite Suche wird benutzt
    s = metrics.summary(sid)
    assert s["tool_searches"] == 2 and s["searches_unused"] == 1
    by_query = {e["query"]: e for e in s["events"] if e["kind"] == "search_tools"}
    assert by_query["Bild erzeugen"]["used"] is False                          # gesucht, nichts benutzt
    assert by_query["im Web suchen"]["used"] is True
    assert s["unused_queries"] == ["Bild erzeugen"]


def test_benutzung_vor_der_suche_zaehlt_nicht(sitzung, tmp_path, monkeypatch):
    """Nur ein run NACH der Suche macht sie zu „benutzt“."""
    from hydrahive.catalog import metrics
    sid = sitzung()
    _run_tool(tmp_path, sid, "web_search", {"query": "x"}, monkeypatch)
    _find_tools(tmp_path, sid, "im Web suchen", {"web_search"}, monkeypatch)
    s = metrics.summary(sid)
    assert s["searches_unused"] == 1 and s["unused_queries"] == ["im Web suchen"]


def test_find_skills_wird_erfasst(sitzung, tmp_path, monkeypatch):
    from hydrahive.catalog import metrics
    from hydrahive.tools import find_skills
    sid = sitzung()
    monkeypatch.setattr(find_skills, "_agent_for", lambda ctx: {"id": "a1", "owner": "testuser", "disabled_skills": []})
    from hydrahive.skills.loader import install_system_defaults
    install_system_defaults()
    res = asyncio.run(find_skills.TOOL.execute({"query": "Fehler im Code suchen"}, _ctx(tmp_path, sid)))
    assert res.success and res.output["results"]
    s = metrics.summary(sid)
    assert s["skill_searches"] == 1 and s["tool_searches"] == 0
    ev = s["events"][0]
    assert ev["kind"] == "search_skills" and "debugging" in ev["results"]
    assert ev["used"] is None                                                  # Skill-Benutzung wird (noch) nicht gemessen
    assert s["searches_unused"] == 0                                           # und zählt deshalb nie als „nichts benutzt“


def test_fehlgeschlagener_run_zaehlt_nicht_als_benutzt(sitzung, tmp_path, monkeypatch):
    from hydrahive.catalog import metrics
    sid = sitzung()
    _find_tools(tmp_path, sid, "Mail schicken", {"send_mail"}, monkeypatch)
    _run_tool(tmp_path, sid, "send_mail", {"to": "a@b.de", "subject": "s", "body": "b"}, monkeypatch, ok=False)
    s = metrics.summary(sid)
    assert s["used"] == [] and s["searches_unused"] == 1


def test_abgelehnter_run_wird_nicht_erfasst(sitzung, tmp_path, monkeypatch):
    """Nicht freigegeben → Ablehnung beim Auspacken, nie ein run-Ereignis."""
    from hydrahive.catalog import metrics
    from hydrahive.runner import _runner_tools
    sid = sitzung()
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    tu = {"id": "c1", "name": "run_tool", "input": {"name": "shell_exec", "args": {"cmd": "ls"}}}

    async def go():
        async for _ in _runner_tools.process_tool_uses(
                [tu], ctx=_ctx(tmp_path, sid), allowed_tools=["run_tool", "file_read"], parent_message_id="m1",
                require_confirm=False, tool_result_max_chars=10000):
            pass
    asyncio.run(go())
    assert metrics.summary(sid)["used"] == []


def test_direkter_aufruf_ohne_run_tool_wird_nicht_erfasst(sitzung, tmp_path, monkeypatch):
    from hydrahive.catalog import metrics
    from hydrahive.runner import _runner_tools

    async def fake_exec(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        return ToolResult.ok("ok"), "rec1", 1

    monkeypatch.setattr(_runner_tools, "execute_tool", fake_exec)
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    sid = sitzung()
    tu = {"id": "c1", "name": "file_read", "input": {"path": "x"}}

    async def go():
        async for _ in _runner_tools.process_tool_uses(
                [tu], ctx=_ctx(tmp_path, sid), allowed_tools=["file_read"], parent_message_id="m1",
                require_confirm=False, tool_result_max_chars=10000):
            pass
    asyncio.run(go())
    assert metrics.summary(sid)["events"] == []


def test_schreibfehler_stoert_den_lauf_nicht(sitzung, tmp_path, monkeypatch):
    """Geschluckt und geloggt: weder find_tools noch run_tool scheitern, wenn die Messung nicht schreiben kann."""
    from hydrahive.catalog import metrics

    def kaputt(*a, **k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(metrics, "_insert", kaputt)
    sid = sitzung()
    res = _find_tools(tmp_path, sid, "Bild erzeugen", {"generate_image"}, monkeypatch)
    assert res.success and res.output["results"]
    _run_tool(tmp_path, sid, "generate_image", {"prompt": "x"}, monkeypatch)     # läuft durch, kein Fehler
    monkeypatch.undo()
    assert metrics.summary(sid)["events"] == []


def test_ohne_tabelle_keine_ausnahme(tmp_path, monkeypatch):
    from hydrahive.catalog import metrics
    monkeypatch.setattr(metrics, "_insert", lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("no such table")))
    metrics.record_search("s-x", "search_tools", "q", ["a"])           # darf nicht werfen
    metrics.record_run("s-x", "a")


def test_anfrage_und_treffer_werden_begrenzt(sitzung):
    from hydrahive.catalog import metrics
    sid = sitzung()
    metrics.record_search(sid, "search_tools", "x" * 5000, [f"tool_{i}" for i in range(500)])
    ev = metrics.summary(sid)["events"][0]
    assert len(ev["query"]) <= metrics.MAX_QUERY and len(ev["results"]) <= metrics.MAX_RESULTS


def test_summary_ohne_ereignisse(sitzung):
    from hydrahive.catalog import metrics
    s = metrics.summary(sitzung())
    assert s["events"] == [] and s["searches"] == 0 and s["found"] == [] and s["used"] == []


# ── Route ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_route_besitzer_und_admin_sehen_die_messung(client, auth_headers, admin_headers, sitzung):
    from hydrahive.catalog import metrics
    sid = sitzung("testuser")
    metrics.record_search(sid, "search_tools", "Bild erzeugen", ["generate_image"])
    metrics.record_run(sid, "generate_image")
    for headers in (auth_headers, admin_headers):
        r = client.get(f"/api/catalog/metrics?session_id={sid}", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["session_id"] == sid and body["tool_searches"] == 1 and body["used"] == ["generate_image"]


def test_route_fremde_bekommen_404_ohne_existenzleck(client, auth_headers, sitzung):
    from hydrahive.catalog import metrics
    fremd = sitzung("admin")                                     # gehört dem Admin, nicht testuser
    metrics.record_search(fremd, "search_tools", "geheime Anfrage", ["send_mail"])
    r = client.get(f"/api/catalog/metrics?session_id={fremd}", headers=auth_headers)
    unbekannt = client.get("/api/catalog/metrics?session_id=gibt-es-nicht", headers=auth_headers)
    assert r.status_code in (403, 404) and r.status_code == unbekannt.status_code
    assert r.json() == unbekannt.json()                          # gleiche Antwort: kein Hinweis, ob die Sitzung existiert
    assert "geheime" not in r.text and "send_mail" not in r.text


def test_route_ohne_anmeldung_und_ohne_session_id(client, auth_headers, sitzung):
    sid = sitzung()
    assert client.get(f"/api/catalog/metrics?session_id={sid}").status_code == 401
    assert client.get("/api/catalog/metrics", headers=auth_headers).status_code == 422


def test_route_identitaet_nur_aus_dem_token(client, auth_headers, sitzung):
    """Ein user/username in der Query ändert nichts: fremde Sitzung bleibt fremd."""
    fremd = sitzung("admin")
    r = client.get(f"/api/catalog/metrics?session_id={fremd}&username=admin&user_id=admin&role=admin", headers=auth_headers)
    assert r.status_code in (403, 404)


def test_sitzung_loeschen_raeumt_messung_mit_auf(sitzung):
    """Review #787: Suchtexte dürfen das Löschen der Sitzung nicht überleben; fremde Sitzungen bleiben unberührt."""
    from hydrahive.catalog import metrics
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db.connection import db
    weg, bleibt = sitzung(), sitzung()
    metrics.record_search(weg, "search_tools", "geheime anfrage", ["web_search"])
    metrics.record_run(weg, "web_search")
    metrics.record_search(bleibt, "search_tools", "andere", [])
    sessions_db.delete(weg)
    with db() as conn:
        rest = {r["session_id"] for r in conn.execute(
            "SELECT session_id FROM catalog_events WHERE session_id IN (?, ?)", (weg, bleibt))}
    assert rest == {bleibt}
