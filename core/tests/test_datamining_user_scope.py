"""Datamining ist benutzergebunden (Security-Task ba5fd3c3).

Vorher: jeder Login las über /api/datamining alle Gespräche aller Nutzer,
durfte Embeddings zurücksetzen und Importe starten; Recall C und die
datamining_*-Agenten-Tools suchten ohne Nutzerfilter.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mirror_on(monkeypatch):
    from hydrahive.db import mirror
    monkeypatch.setattr(mirror, "_pool", object())


# ── REST-API: Lesen ────────────────────────────────────────────────────────

def test_search_erzwingt_eigenen_user_fuer_nicht_admins(client, auth_headers, mirror_on):
    seen = {}

    async def fake_search(q, **kw):
        seen.update(kw)
        return []

    with patch("hydrahive.db.mirror_query.search_events", side_effect=fake_search):
        r = client.get("/api/datamining/search?q=x&username=admin", headers=auth_headers)
    assert r.status_code == 200
    assert seen["username"] == "testuser"


def test_search_admin_darf_filtern_und_alles_sehen(client, admin_headers, mirror_on):
    seen = {}

    async def fake_search(q, **kw):
        seen.update(kw)
        return []

    with patch("hydrahive.db.mirror_query.search_events", side_effect=fake_search):
        client.get("/api/datamining/search?q=x", headers=admin_headers)
        assert seen["username"] is None
        client.get("/api/datamining/search?q=x&username=testuser", headers=admin_headers)
        assert seen["username"] == "testuser"


def test_sessions_liste_nur_eigene(client, auth_headers, mirror_on):
    seen = {}

    async def fake_list(**kw):
        seen.update(kw)
        return []

    with patch("hydrahive.db.mirror_query.list_sessions", side_effect=fake_list):
        client.get("/api/datamining/sessions?username=admin", headers=auth_headers)
    assert seen["username"] == "testuser"


def test_fremde_session_detail_ist_404(client, auth_headers, mirror_on):
    detail = {"session": {"id": "s1", "username": "admin"}, "events": []}
    with patch("hydrahive.db.mirror_query.get_session_detail", AsyncMock(return_value=detail)):
        r = client.get("/api/datamining/sessions/s1", headers=auth_headers)
    assert r.status_code == 404


def test_eigene_session_detail_ok(client, auth_headers, mirror_on):
    detail = {"session": {"id": "s1", "username": "testuser"}, "events": []}
    with patch("hydrahive.db.mirror_query.get_session_detail", AsyncMock(return_value=detail)):
        r = client.get("/api/datamining/sessions/s1", headers=auth_headers)
    assert r.status_code == 200


def test_live_feed_und_graph_nur_eigene(client, auth_headers, mirror_on):
    from hydrahive.db import mirror
    feed = AsyncMock(return_value=[])
    graph = AsyncMock(return_value={"nodes": []})
    with patch.object(mirror, "recent_events", feed), \
         patch("hydrahive.db.mirror_graph_topology.build_topology", graph):
        client.get("/api/datamining/events", headers=auth_headers)
        client.get("/api/datamining/graph", headers=auth_headers)
    assert feed.call_args.kwargs["username"] == "testuser"
    assert graph.call_args.kwargs["username"] == "testuser"


# ── REST-API: Admin-Aktionen ──────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/datamining/embed/reset",
    "/api/datamining/embed/rechunk",
    "/api/datamining/embed/backfill",
    "/api/datamining/import/sqlite",
    "/api/datamining/import/git",
    "/api/datamining/import/jsonl",
    "/api/datamining/import/logs",
])
def test_admin_aktionen_fuer_nicht_admins_verboten(client, auth_headers, path):
    assert client.post(path, headers=auth_headers).status_code == 403


def test_shell_import_fuer_nicht_admins_verboten(client, auth_headers):
    r = client.post("/api/datamining/import/shell-history", headers=auth_headers,
                    files={"file": ("h.txt", b"ls\n")})
    assert r.status_code == 403


# ── Token-Statistik ────────────────────────────────────────────────────────

def test_stats_latest_nur_eigene_sessions(client, auth_headers):
    from hydrahive.db import init_db
    from hydrahive.db import sessions as sessions_db
    init_db()
    mine = sessions_db.create(agent_id="a", user_id="testuser", title="meins")
    other = sessions_db.create(agent_id="a", user_id="admin", title="GEHEIM-admin")
    try:
        r = client.get("/api/datamining/stats/latest?count=50", headers=auth_headers)
        titles = {s["title"] for s in r.json()["sessions"]}
        assert "meins" in titles and "GEHEIM-admin" not in titles
        assert client.get(f"/api/datamining/stats/session/{other.id}",
                          headers=auth_headers).status_code == 404
    finally:
        sessions_db.delete(mine.id)
        sessions_db.delete(other.id)


# ── Agenten-Tools + Recall ────────────────────────────────────────────────

@pytest.mark.parametrize("tool_name", [
    "datamining_search", "datamining_semantic", "datamining_timeline", "datamining_today",
])
def test_datamining_tools_filtern_auf_session_user(tool_name):
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import ToolContext

    calls: list[dict] = []

    async def fake(*a, **kw):
        calls.append(kw)
        return []

    ctx = ToolContext(session_id="s", agent_id="a", user_id="alice", workspace=None, config={})
    with patch("hydrahive.db.mirror_query.search_events", side_effect=fake), \
         patch("hydrahive.db.mirror_query.list_sessions", side_effect=fake):
        asyncio.run(REGISTRY[tool_name].execute({"query": "x"}, ctx))
    assert calls and all(c.get("username") == "alice" for c in calls)


def test_recall_kartensuche_filtert_auf_user():
    import inspect
    from hydrahive.db._mirror_cards import search_cards, top_cards_for
    assert "username" in inspect.signature(search_cards).parameters
    assert "username" in inspect.signature(top_cards_for).parameters
