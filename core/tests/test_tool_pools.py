"""Katalog Etappe 5, Aufgabe 6 (Backend): Freigabe-Pool, Besitzer-Freigabe, Projekt-Pool (Spec E1/E3/E5/S3/S5, K13/K14/K16).

Der Pool eines Agenten sagt, welche Tools ihm (per ask_agent) pro Auftrag zugewiesen werden dürfen. Genau eine Quelle:
``agents/tool_pools.py`` (Tabellen aus Migration 068). Das Config-Feld ``tool_pool`` gibt es nicht mehr.
"""
from __future__ import annotations

import sqlite3

import pytest

from hydrahive.agents import config as agent_config

TABLES = ("owner_tool_grants", "agent_tool_pools", "project_tool_pools")


def _clear() -> None:
    from hydrahive.db.connection import db
    with db() as conn:
        for t in TABLES:
            try:
                conn.execute(f"DELETE FROM {t}")
            except sqlite3.OperationalError:
                pass


@pytest.fixture(autouse=True)
def _sauber(setup_test_env):
    from hydrahive.db import init_db
    init_db()
    _clear()
    yield
    _clear()


@pytest.fixture
def made(client):
    created: list[str] = []

    def make(name: str, owner: str = "testuser", agent_type: str = "specialist", tools=None) -> dict:
        a = agent_config.create(agent_type=agent_type, name=name, llm_model="claude-sonnet-4-6", owner=owner,
                                tools=list(tools if tools is not None else ["file_read"]),
                                temperature=0.7, max_tokens=1000, thinking_budget=0)
        created.append(a["id"])
        return a

    yield make
    for aid in created:
        agent_config.delete(aid)


@pytest.fixture
def projekt(client):
    from hydrahive.projects import config as project_config
    made: list[str] = []

    def make(name: str, *, created_by: str = "admin", members=None) -> dict:
        p = project_config.create(name=name, llm_model="claude-sonnet-4-6", created_by=created_by, members=members or [])
        made.append(p["id"])
        return p

    yield make
    for pid in made:
        try:
            project_config.delete(pid)
        except Exception:                               # noqa: BLE001 — Aufräumen
            pass


def _put(client, headers, url: str, items, **extra):
    return client.put(url, headers=headers, json={"items": items, **extra})


# ── Migration / Struktur ──────────────────────────────────────────────────────────────────────────────────────────

def test_migration_068_tabellen_da():
    from hydrahive.db.connection import db
    with db() as conn:
        for t, col in (("owner_tool_grants", "username"), ("agent_tool_pools", "agent_id"),
                       ("project_tool_pools", "project_id")):
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({t})")}
            assert {col, "tool_or_category"} <= cols, t


# ── S3: Authoring und ask_agent nie im Pool ───────────────────────────────────────────────────────────────────────

def test_pool_ohne_authoring_und_ask_agent(made):
    from hydrahive.agents import tool_pools
    from hydrahive.db.connection import db
    a = made("Pool-Agent")
    for verboten in ("ask_agent", "create_specialist", "configure_specialist", "write_skill", "delete_skill",
                     "list_specialists", "find_tools", "run_tool"):
        with pytest.raises(ValueError):
            tool_pools.set_agent_pool("admin", a["id"], [verboten])
    with pytest.raises(ValueError):
        tool_pools.set_agent_pool("admin", a["id"], ["kategorie:gibt-es-nicht"])
    with pytest.raises(ValueError):
        tool_pools.set_agent_pool("admin", a["id"], ["tool|mit,Trennzeichen"])
    tool_pools.set_agent_pool("admin", a["id"], ["file_read", "web_search"])
    with db() as conn:                                   # selbst eine am Schutz vorbei geschriebene Zeile wirkt nicht
        for t in ("ask_agent", "create_specialist", "write_skill"):
            conn.execute("INSERT INTO agent_tool_pools(agent_id, tool_or_category) VALUES (?, ?)", (a["id"], t))
    pool = tool_pools.tool_pool_for(agent_config.get(a["id"]), None)
    assert pool == ["file_read", "web_search"]


# ── E5 / K16: Besitzer-Freigabe ───────────────────────────────────────────────────────────────────────────────────

def test_ohne_besitzer_freigabe_nichts_vergebbar(client, auth_headers, made):
    a = made("Eigener")
    r = _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", ["file_read"])
    assert r.status_code == 403
    assert _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", []).status_code == 200    # leer ist immer ok


def test_nicht_admin_ausserhalb_besitzer_freigabe_403(client, auth_headers, admin_headers, made):
    a = made("Eigener")
    assert _put(client, admin_headers, "/api/admin/tool-grants/testuser", ["file_read"]).status_code == 200
    r = _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", ["file_read", "web_search"])
    assert r.status_code == 403
    ok = _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", ["file_read"])
    assert ok.status_code == 200 and ok.json()["items"] == ["file_read"]


def test_freigabe_einer_kategorie_deckt_ihre_tools(client, auth_headers, admin_headers, made):
    a = made("Eigener")
    assert _put(client, admin_headers, "/api/admin/tool-grants/testuser", ["kategorie:files"]).status_code == 200
    assert _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", ["file_read", "file_write"]).status_code == 200
    assert _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", ["web_search"]).status_code == 403


def test_admin_ungedeckelt(client, admin_headers, made):
    a = made("Fremder", owner="testuser")
    r = _put(client, admin_headers, f"/api/agents/{a['id']}/tool-pool", ["web_search", "send_mail", "shell_exec"])
    assert r.status_code == 200 and r.json()["items"] == ["web_search", "send_mail", "shell_exec"]


def test_besitzer_freigabe_nur_admin_und_identitaet_aus_token(client, auth_headers, admin_headers, made):
    from hydrahive.agents import tool_pools
    assert _put(client, auth_headers, "/api/admin/tool-grants/testuser", ["file_read"]).status_code == 403
    with pytest.raises(PermissionError):
        tool_pools.set_owner_grants("testuser", "testuser", ["file_read"])
    a = made("Eigener")
    # Ein „actor“/„by“ im Body ändert nichts: die Identität kommt aus dem Token.
    r = _put(client, auth_headers, f"/api/agents/{a['id']}/tool-pool", ["send_mail"], actor="admin", by="admin")
    assert r.status_code == 403


def test_freigabe_entzogen_pool_wirkt_nicht_mehr(client, admin_headers, made):
    """Lesezeit-Schnitt: Wird die Besitzer-Freigabe später kleiner, schrumpft der wirksame Pool mit (E5)."""
    from hydrahive.agents import tool_pools
    a = made("Eigener")
    tool_pools.set_owner_grants("admin", "testuser", ["file_read", "web_search"])
    tool_pools.set_agent_pool("testuser", a["id"], ["file_read", "web_search"])
    assert tool_pools.tool_pool_for(agent_config.get(a["id"]), None) == ["file_read", "web_search"]
    tool_pools.set_owner_grants("admin", "testuser", ["file_read"])
    assert tool_pools.tool_pool_for(agent_config.get(a["id"]), None) == ["file_read"]


# ── S5 / K14: wer setzt welchen Pool ──────────────────────────────────────────────────────────────────────────────

def test_write_mitglied_setzt_pool_403(client, auth_headers, projekt):
    p = projekt("pool-projekt", members=[{"username": "testuser", "role": "write"}])
    r = _put(client, auth_headers, f"/api/agents/{p['agent_id']}/tool-pool", [])          # Projekt-Agent gehört dem Admin
    assert r.status_code == 403
    assert _put(client, auth_headers, f"/api/projects/{p['id']}/tool-pool", ["file_read"]).status_code == 403


def test_projekt_admin_setzt_projekt_pool(client, auth_headers, admin_headers, projekt):
    p = projekt("pool-projekt-2", members=[{"username": "testuser", "role": "admin"}])
    r = _put(client, auth_headers, f"/api/projects/{p['id']}/tool-pool", ["file_read", "web_search"])
    assert r.status_code == 200 and r.json()["items"] == ["file_read", "web_search"]
    assert client.get(f"/api/projects/{p['id']}/tool-pool", headers=auth_headers).json()["items"] == ["file_read", "web_search"]
    assert _put(client, admin_headers, f"/api/projects/{p['id']}/tool-pool", []).status_code == 200


def test_wirksam_agenten_pool_schnitt_projekt_pool(made, projekt):
    from hydrahive.agents import tool_pools
    p = projekt("schnitt-projekt")
    a = made("Projekt-Spezialist", owner="admin")
    tool_pools.set_agent_pool("admin", a["id"], ["file_read", "web_search", "read_mail"])
    agent = agent_config.get(a["id"])
    assert tool_pools.tool_pool_for(agent, p) == ["file_read", "web_search", "read_mail"]        # Projekt-Pool leer = frei
    tool_pools.set_project_pool("admin", p["id"], ["web_search", "read_mail", "generate_image"])
    assert tool_pools.tool_pool_for(agent, p) == ["web_search", "read_mail"]                     # Projekte schränken nur ein
    tool_pools.set_project_pool("admin", p["id"], ["generate_image"])
    assert tool_pools.tool_pool_for(agent, p) == []                                              # nie erweitern


# ── KP5: genau eine Quelle ────────────────────────────────────────────────────────────────────────────────────────

def test_patch_tool_pool_ueber_agenten_api_abgelehnt(client, admin_headers, made):
    from hydrahive.agents import tool_pools
    a = made("Patch-Ziel", owner="admin")
    r = client.patch(f"/api/agents/{a['id']}", headers=admin_headers, json={"tool_pool": ["shell_exec"]})
    assert r.status_code == 400
    assert "tool_pool" not in agent_config.get(a["id"])
    assert tool_pools.tool_pool_for(agent_config.get(a["id"]), None) == []
    with pytest.raises(agent_config.AgentValidationError if hasattr(agent_config, "AgentValidationError") else Exception):
        agent_config.update(a["id"], tool_pool=["shell_exec"])


def test_possible_und_effective_nutzen_dieselbe_quelle(made):
    from hydrahive.agents import tool_pools
    from hydrahive.agents.effective_tools import effective_tool_names, possible_tool_names
    from hydrahive.db._mirror_groups import has_outward_tools
    a = made("Quelle", owner="admin", tools=["file_read"])
    agent = agent_config.get(a["id"])
    assert has_outward_tools(sorted(possible_tool_names(agent))) is False
    tool_pools.set_agent_pool("admin", a["id"], ["send_mail"])
    assert "send_mail" in possible_tool_names(agent_config.get(a["id"]))          # Gedächtnis-Sicht: könnte er bekommen
    assert has_outward_tools(sorted(possible_tool_names(agent_config.get(a["id"])))) is True
    assert "tool_pool" not in agent_config.get(a["id"])                            # das Config-Feld gibt es nicht mehr
    got = effective_tool_names(agent_config.get(a["id"]), username="admin", project=None)
    assert "send_mail" not in got                                                  # ohne Zuweisung kein Recht
    assert "send_mail" in effective_tool_names(agent_config.get(a["id"]), username="admin", project=None,
                                               pool=tool_pools.tool_pool_for(agent_config.get(a["id"]), None))


def test_can_delegate_beruecksichtigt_den_pool_pfad(monkeypatch):
    from hydrahive.agentlink.runtime_profiles import can_delegate
    from hydrahive.agents import effective_tools
    assert can_delegate({"id": "x", "tools": ["ask_agent"]}) is True
    assert can_delegate({"id": "x", "tools": ["file_read"]}) is False
    monkeypatch.setattr(effective_tools, "possible_tool_names", lambda agent: {"ask_agent"})
    assert can_delegate({"id": "x", "tools": []}) is True                          # die gemeinsame Quelle entscheidet


def test_pool_loeschen_mit_agent(made):
    from hydrahive.agents import tool_pools
    a = made("Weg")
    tool_pools.set_agent_pool("admin", a["id"], ["file_read"])
    agent_config.delete(a["id"])
    assert tool_pools.agent_pool_items(a["id"]) == []
