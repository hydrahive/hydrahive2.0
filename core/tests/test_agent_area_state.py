"""Agenten-Bereiche, Aufgabe 3 (AB3/AB4, Backend): Status, Umschalten, ``area_seen`` und ``GET /api/agents/{id}/areas``.

Bereiche sind nur eine SICHT auf ``agent.tools`` (E1, Spec 4.2): ``toggle`` ist rein funktional, gespeichert wird über das
bestehende ``PATCH /api/agents/{id}`` (Admin, Spec 4.8). ``area_seen`` merkt sich beim Speichern der Tools, welche Tools es
je Bereich damals gab – so ist „neu“ nur, was damals noch nicht existierte (Review #789 M6).
"""
from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config

FILES_READ = ["file_read", "read_document"]
FILES_WRITE = ["file_patch", "file_write"]


def _state(agent: dict, area_id: str) -> dict:
    from hydrahive.agents.area_state import area_states
    return next(s for s in area_states(agent) if s["id"] == area_id)


@pytest.fixture
def fake_tool(monkeypatch):
    """Registriert ein zusätzliches Tool im Bereich ``files_read`` (Muster: Modul-Zuordnung über agent_areas)."""
    from pathlib import Path
    from hydrahive.modules import registry as mreg
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("x")

    def add(name: str = "fake_lesen", area: str = "files_read") -> str:
        monkeypatch.setitem(REGISTRY, name, Tool(name=name, description=name, schema={"type": "object", "properties": {}},
                                                 execute=_x, module_id="fake-mod"))
        manifest = ModuleManifest(id="fake-mod", name="Fake", version="1", agent_areas=({"area": area, "tools": [name]},))
        monkeypatch.setitem(mreg.REGISTRY, "fake-mod", mreg.LoadedModule(
            name="fake-mod", manifest=manifest, path=Path("/nonexistent"), loaded=True))
        return name
    return add


@pytest.fixture
def made(client):
    created: list[str] = []

    def make(tools=None, owner: str = "testuser", agent_type: str = "specialist") -> dict:
        a = agent_config.create(agent_type=agent_type, name=f"bereich-{len(created)}", llm_model="claude-sonnet-4-6",
                                owner=owner, tools=list(tools if tools is not None else []),
                                temperature=0.7, max_tokens=1000, thinking_budget=0)
        created.append(a["id"])
        return a
    yield make
    for aid in created:
        agent_config.delete(aid)


# ── toggle (rein funktional) ──────────────────────────────────────────────────────────────────────────────────────

def test_toggle_an_aus_nur_eigene_tools():
    from hydrahive.agents.area_state import toggle
    start = ["web_search", "file_read"]
    an = toggle(start, "files_write", True)
    assert an == ["web_search", "file_read", "file_patch", "file_write"]       # nur hinten angehängt, Reihenfolge stabil
    assert toggle(an, "files_write", False) == start                            # Gegenprobe: genau diese wieder raus
    assert toggle(start, "files_write", False) == start                         # Ausschalten ohne die Tools ändert nichts
    assert toggle(an, "files_write", True) == an                                # Einschalten ist idempotent, keine Dubletten
    assert start == ["web_search", "file_read"]                                 # Eingabe bleibt unverändert


def test_schalter_laesst_fremde_tools_stehen():
    """Review-Fokus 1: Plugin-, MCP- und Altbestand-Namen gehen beim Umschalten nie verloren."""
    from hydrahive.agents.area_state import toggle
    start = ["plugin__x__y", "mcp__a__b", "altlast_tool", "file_write", "kategorie:memory"]
    assert toggle(start, "files_write", False) == ["plugin__x__y", "mcp__a__b", "altlast_tool", "kategorie:memory"]
    an = toggle(start, "files_read", True)
    assert {"plugin__x__y", "mcp__a__b", "altlast_tool", "kategorie:memory"} <= set(an)
    assert toggle(an, "files_read", False) == start


def test_toggle_laesst_base_tools_stehen():
    from hydrahive.agents.area_state import toggle
    start = ["find_tools", "run_tool", "todo_write", "list_skills", "file_write"]
    assert toggle(start, "files_write", False) == ["find_tools", "run_tool", "todo_write", "list_skills"]
    assert toggle(["find_tools"], "files_write", True)[0] == "find_tools"


def test_toggle_unbekannter_bereich():
    from hydrahive.agents.area_state import toggle
    with pytest.raises(KeyError):
        toggle(["file_read"], "gibt_es_nicht", True)


def test_toggle_schreibt_nie_bereich_x():
    """E1: Es wird nie ``bereich:x`` gespeichert, nur Tool-Namen."""
    from hydrahive.agents.area_state import toggle
    assert not any(t.startswith(("bereich", "area")) for t in toggle([], "files_write", True))


# ── Status ────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_status_on_off_partial():
    assert _state({"tools": FILES_READ}, "files_read")["state"] == "on"
    off = _state({"tools": ["web_search"]}, "files_read")
    assert off["state"] == "off" and off["have"] == [] and off["missing"] == FILES_READ
    partial = _state({"tools": ["file_read"]}, "files_read")
    assert partial["state"] == "partial" and partial["have"] == ["file_read"] and partial["missing"] == ["read_document"]
    assert _state({"tools": []}, "files_read")["state"] == "off"
    assert {"id", "state", "have", "missing", "new", "via_category"} <= set(off)


def test_status_alle_bereiche_geliefert():
    from hydrahive.agents._area_registry import all_areas
    from hydrahive.agents.area_state import area_states
    states = area_states({"tools": []})
    assert [s["id"] for s in states] == [a["id"] for a in all_areas()]
    assert all(s["state"] == "off" for s in states if s["have"] == [])


def test_status_teilweise_durch_kategorie():
    """Review-Fokus 4: Kommt ein Teil nur über ``kategorie:x``, ist der Schalter „teilweise“, nie „aus“; via_category sagt woher."""
    s = _state({"tools": ["kategorie:files"]}, "files_read")
    assert s["via_category"] == FILES_READ and s["have"] == []
    assert s["state"] == "partial"
    # ausschalten (toggle) entfernt nur die einzelnen Tool-Namen, die Kategorie bleibt → bleibt „teilweise“
    from hydrahive.agents.area_state import toggle
    nach = toggle(["kategorie:files", "file_read"], "files_read", False)
    assert nach == ["kategorie:files"]
    assert _state({"tools": nach}, "files_read")["state"] == "partial"
    gemischt = _state({"tools": ["kategorie:files", "file_read"]}, "files_read")
    assert gemischt["have"] == ["file_read"] and gemischt["via_category"] == ["read_document"]
    # Es fehlt nichts (der Rest kommt über die Kategorie), also gilt der Bereich als „an“; via_category sagt ehrlich woher
    assert gemischt["state"] == "on" and gemischt["missing"] == []


def test_status_kategorie_deckt_fremde_bereiche_nicht():
    s = _state({"tools": ["kategorie:files"]}, "shell")
    assert s["state"] == "off" and s["via_category"] == []


# ── „neu“ über area_seen (Review #789 M6) ─────────────────────────────────────────────────────────────────────────

def test_ohne_area_seen_gelten_alle_heutigen_tools_als_gesehen(fake_tool):
    fake_tool()
    s = _state({"tools": FILES_READ}, "files_read")                 # kein area_seen: „alles gesehen“
    assert s["new"] == [] and s["state"] == "partial" and s["missing"] == ["fake_lesen"]


def test_new_zeigt_neu_registriertes_tool(fake_tool):
    """Der Bereich ist voll und gespeichert, danach kommt ein Tool dazu → ``on`` mit ``new``."""
    from hydrahive.agents.area_state import seen_snapshot
    agent = {"tools": FILES_READ, "area_seen": seen_snapshot()}     # gespeichert, bevor das Tool existierte
    fake_tool()
    s = _state(agent, "files_read")
    assert s["state"] == "on" and s["new"] == ["fake_lesen"] and s["missing"] == ["fake_lesen"]
    assert s["have"] == FILES_READ
    # Ohne Klick ändert sich nichts: area_states schreibt nichts in den Agenten
    assert agent["tools"] == FILES_READ


def test_absichtlich_entferntes_tool_ist_nicht_neu():
    """M6: Der Bereich war voll, ein Tool wurde entfernt und gespeichert → ``partial`` ohne ``new``."""
    from hydrahive.agents.area_state import seen_snapshot
    agent = {"tools": ["file_read"], "area_seen": seen_snapshot()}
    s = _state(agent, "files_read")
    assert s["state"] == "partial" and s["new"] == [] and s["missing"] == ["read_document"]


def test_new_nur_im_betroffenen_bereich(fake_tool):
    from hydrahive.agents.area_state import area_states, seen_snapshot
    agent = {"tools": FILES_READ, "area_seen": seen_snapshot()}
    fake_tool()
    assert {s["id"]: s["new"] for s in area_states(agent) if s["new"]} == {"files_read": ["fake_lesen"]}


def test_seen_snapshot_je_bereich_registrierte_tools():
    from hydrahive.agents.area_state import seen_snapshot
    snap = seen_snapshot()
    assert snap["files_read"] == FILES_READ and snap["shell"] == ["shell_exec"]
    assert set(snap) >= {"files_read", "shell", "memory"}


def test_new_ignoriert_kaputtes_area_seen():
    for kaputt in ("text", ["x"], 5, {"files_read": "text"}, {"files_read": [1, 2]}):
        s = _state({"tools": FILES_READ, "area_seen": kaputt}, "files_read")
        assert s["state"] == "on" and s["new"] == []


# ── area_seen beim Speichern ──────────────────────────────────────────────────────────────────────────────────────

def test_update_tools_schreibt_area_seen(made):
    from hydrahive.agents.area_state import seen_snapshot
    a = made(tools=[])
    assert "area_seen" not in agent_config.get(a["id"]) or agent_config.get(a["id"]).get("area_seen") in (None, {})
    updated = agent_config.update(a["id"], tools=FILES_READ)
    assert updated["area_seen"] == seen_snapshot()
    assert agent_config.get(a["id"])["area_seen"]["files_read"] == FILES_READ


def test_update_ohne_tools_laesst_area_seen_in_ruhe(made):
    a = made(tools=FILES_READ)
    agent_config.update(a["id"], tools=FILES_READ)
    vorher = agent_config.get(a["id"])["area_seen"]
    agent_config.update(a["id"], description="nur eine Beschreibung")
    assert agent_config.get(a["id"])["area_seen"] == vorher


def test_create_setzt_kein_area_seen(made):
    """Ein fehlender Wert heißt „alles gesehen“ (Spec): beim Anlegen und Laden kein Standardwert."""
    a = made(tools=FILES_READ)
    assert not agent_config.get(a["id"]).get("area_seen")


def test_area_seen_nicht_per_api_setzbar(client, admin_headers, made):
    a = made(tools=FILES_READ)
    r = client.patch(f"/api/agents/{a['id']}", headers=admin_headers, json={"area_seen": {"files_read": ["x"]}})
    assert r.status_code in (200, 400, 422)
    assert not agent_config.get(a["id"]).get("area_seen")                         # nichts übernommen
    r2 = client.patch(f"/api/agents/{a['id']}", headers=admin_headers, json={"tools": FILES_READ + ["web_search"]})
    assert r2.status_code == 200
    gespeichert = agent_config.get(a["id"])["area_seen"]
    assert gespeichert != {"files_read": ["x"]} and gespeichert["files_read"] == FILES_READ   # Server schreibt, nicht der Client


def test_area_seen_nicht_im_agent_update_schema():
    from hydrahive.api.routes._agent_schemas import AgentUpdate
    assert "area_seen" not in AgentUpdate.model_fields


# ── Route ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_areas_route_nur_besitzer_admin(client, auth_headers, admin_headers, made):
    eigener = made(tools=FILES_READ, owner="testuser")
    fremder = made(tools=FILES_READ, owner="admin")
    assert client.get(f"/api/agents/{eigener['id']}/areas", headers=auth_headers).status_code == 200
    assert client.get(f"/api/agents/{eigener['id']}/areas", headers=admin_headers).status_code == 200
    r = client.get(f"/api/agents/{fremder['id']}/areas", headers=auth_headers)
    assert r.status_code in (403, 404)
    assert client.get(f"/api/agents/{fremder['id']}/areas").status_code == 401
    assert client.get("/api/agents/gibt-es-nicht/areas", headers=auth_headers).status_code == 404


def test_areas_route_fremd_wie_tool_pool(client, auth_headers, made):
    """Fremder Agent: dieselbe Antwort wie bei /tool-pool (kein anderer Existenz-Hinweis)."""
    fremder = made(tools=FILES_READ, owner="admin")
    a = client.get(f"/api/agents/{fremder['id']}/areas", headers=auth_headers)
    b = client.get(f"/api/agents/{fremder['id']}/tool-pool", headers=auth_headers)
    assert a.status_code == b.status_code and a.json() == b.json()
    assert "file_read" not in a.text


def test_areas_route_liefert_zustaende(client, auth_headers, made):
    a = made(tools=["file_read", "shell_exec"], owner="testuser")
    body = client.get(f"/api/agents/{a['id']}/areas", headers=auth_headers).json()
    assert set(body) == {"areas", "editable"}
    by_id = {s["id"]: s for s in body["areas"]}
    assert by_id["shell"]["state"] == "on" and by_id["files_read"]["state"] == "partial"
    assert by_id["files_read"]["have"] == ["file_read"] and by_id["files_read"]["missing"] == ["read_document"]
    assert by_id["web_search"]["state"] == "off"


def test_areas_route_editable_nur_admin(client, auth_headers, admin_headers, made):
    a = made(tools=FILES_READ, owner="testuser")
    assert client.get(f"/api/agents/{a['id']}/areas", headers=auth_headers).json()["editable"] is False
    assert client.get(f"/api/agents/{a['id']}/areas", headers=admin_headers).json()["editable"] is True


def test_areas_route_ist_nur_lesend(client, auth_headers, made):
    a = made(tools=[], owner="testuser")
    client.get(f"/api/agents/{a['id']}/areas", headers=auth_headers)
    assert agent_config.get(a["id"])["tools"] == []
    for method in (client.put, client.post, client.patch, client.delete):
        assert method(f"/api/agents/{a['id']}/areas", headers=auth_headers).status_code in (404, 405)


def test_patch_bleibt_admin_only(client, auth_headers, made):
    a = made(tools=[], owner="testuser")
    assert client.patch(f"/api/agents/{a['id']}", headers=auth_headers, json={"tools": ["shell_exec"]}).status_code == 403
    assert agent_config.get(a["id"])["tools"] == []
