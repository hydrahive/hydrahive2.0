"""Agenten-Bereiche, Aufgabe 2 (AB2): Module melden Bereiche, die Route liefert das Verzeichnis (Spec 4.1)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from hydrahive.modules.manifest import ManifestError, ModuleManifest


def _manifest(tmp_path: Path, **extra) -> ModuleManifest:
    d = {"id": "fake-mod", "name": "Fake", "version": "1.0.0", **extra}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(d))
    return ModuleManifest.load(p)


NEUER_BEREICH = {"id": "vr_studio", "group": "creative", "name": {"de": "VR-Studio", "en": "VR studio"},
                 "sentence": {"de": "VR-Szenen bauen", "en": "Build VR scenes"}, "marks": ["costly"], "tools": ["vr_*"]}


@pytest.fixture
def modul(monkeypatch):
    """Meldet ein Fake-Modul samt Tools an (ohne echtes Laden): Manifest + Tool-Namen in REGISTRY."""
    from hydrahive.modules import registry as mreg
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("x")

    def install(manifest: ModuleManifest, tool_names: list[str], module_id: str = "fake-mod") -> None:
        for n in tool_names:
            monkeypatch.setitem(REGISTRY, n, Tool(name=n, description=n, schema={"type": "object", "properties": {}},
                                                  execute=_x, module_id=module_id))
        monkeypatch.setitem(mreg.REGISTRY, module_id, mreg.LoadedModule(
            name=module_id, manifest=manifest, path=Path("/nonexistent"), loaded=True))
    return install


# ── Manifest ──────────────────────────────────────────────────────────────────────────────────────────────────────

def test_manifest_ohne_agent_areas_unveraendert(tmp_path):
    m = _manifest(tmp_path)
    assert m.agent_areas == ()
    assert m.id == "fake-mod" and m.capabilities == () and m.templates == ()


def test_manifest_parst_zuordnung_und_neuen_bereich(tmp_path):
    m = _manifest(tmp_path, agent_areas=[{"area": "home_control", "tools": ["ha_scene_activate"]}, NEUER_BEREICH])
    assert len(m.agent_areas) == 2
    assert m.agent_areas[0]["area"] == "home_control" and m.agent_areas[0]["tools"] == ["ha_scene_activate"]
    assert m.agent_areas[1]["id"] == "vr_studio" and m.agent_areas[1]["marks"] == ["costly"]


@pytest.mark.parametrize("kaputt", [
    "kein-array",
    [{"tools": ["a"]}],                                                           # weder area noch id
    [{"area": "home_control", "tools": "ha_x"}],                                  # tools keine Liste
    [{"area": "home_control", "tools": ["gr*ph"]}],                               # Stern mitten im Namen
    [{"id": "x", "group": "internet", "tools": ["a"]}],                           # Name/Satz fehlen
    [{"id": "x", "group": "gibt-es-nicht", "name": {"de": "a", "en": "a"}, "sentence": {"de": "a", "en": "a"},
      "tools": ["a"]}],
])
def test_manifest_kaputtes_agent_areas_wird_abgelehnt(tmp_path, kaputt):
    with pytest.raises(ManifestError):
        _manifest(tmp_path, agent_areas=kaputt)


# ── Verzeichnis ───────────────────────────────────────────────────────────────────────────────────────────────────

def test_kernbereiche_ohne_module():
    from hydrahive.agents._area_registry import all_areas
    areas = all_areas("de")
    assert len(areas) >= 26 and {a["id"] for a in areas} >= {"files_read", "shell", "home_control"}
    shell = next(a for a in areas if a["id"] == "shell")
    assert shell["source"] == "core" and shell["tools"] == ["shell_exec"] and shell["name"] == "Befehle ausführen"
    assert set(shell) >= {"id", "group", "name", "sentence", "marks", "tools", "source"}
    assert next(a for a in all_areas("en") if a["id"] == "shell")["name"] == "Run commands"


def test_unbekannte_sprache_faellt_auf_deutsch():
    from hydrahive.agents._area_registry import all_areas
    assert next(a for a in all_areas("xx") if a["id"] == "shell")["name"] == "Befehle ausführen"


def test_modul_zuordnung_landet_im_bereich(modul, tmp_path):
    from hydrahive.agents._area_registry import all_areas, area_of
    modul(_manifest(tmp_path, agent_areas=[{"area": "home_control", "tools": ["fake_tool"]}]), ["fake_tool"])
    assert area_of("fake_tool") == "home_control"
    area = next(a for a in all_areas() if a["id"] == "home_control")
    assert "fake_tool" in area["tools"] and area["source"] == "core"


def test_modul_neuer_bereich_mit_muster(modul, tmp_path):
    from hydrahive.agents._area_registry import all_areas, area_of
    modul(_manifest(tmp_path, agent_areas=[NEUER_BEREICH]), ["vr_scene", "vr_render", "anderes"])
    assert area_of("vr_scene") == "vr_studio" and area_of("vr_render") == "vr_studio"
    assert area_of("anderes") is None
    vr = next(a for a in all_areas() if a["id"] == "vr_studio")
    assert vr["tools"] == ["vr_render", "vr_scene"] and vr["source"] == "fake-mod" and vr["marks"] == ["costly"]


def test_modul_darf_kernbereich_nicht_ueberschreiben(modul, tmp_path, caplog):
    from hydrahive.agents._area_registry import all_areas
    from hydrahive.agents.areas import CORE_AREAS
    evil = {**NEUER_BEREICH, "id": "shell", "group": "server", "tools": ["evil_*"]}
    with caplog.at_level(logging.WARNING):
        modul(_manifest(tmp_path, agent_areas=[evil]), ["evil_tool"])
        areas = all_areas()
    shell = [a for a in areas if a["id"] == "shell"]
    assert len(shell) == 1 and shell[0]["source"] == "core" and "evil_tool" not in shell[0]["tools"]
    assert {a.id for a in CORE_AREAS} <= {a["id"] for a in areas}
    assert any("shell" in r.getMessage() for r in caplog.records)             # geloggt


def test_modul_neuer_bereich_mit_vorhandener_id_eines_anderen_moduls_wird_verworfen(modul, tmp_path):
    from hydrahive.agents._area_registry import all_areas
    modul(_manifest(tmp_path, agent_areas=[NEUER_BEREICH]), ["vr_a"], module_id="mod-eins")
    modul(_manifest(tmp_path, agent_areas=[{**NEUER_BEREICH, "tools": ["fremd_*"]}]), ["fremd_a"], module_id="mod-zwei")
    vr = [a for a in all_areas() if a["id"] == "vr_studio"]
    assert len(vr) == 1 and vr[0]["tools"] == ["vr_a"]                         # der erste gewinnt, kein Überschreiben


def test_doppelte_zuordnung_kern_gewinnt(modul, tmp_path, caplog):
    """Review-Fokus 2: Ein Modul ordnet ein Kern-Tool einem anderen Bereich zu → Kern gewinnt, Warnung, nichts doppelt."""
    from hydrahive.agents._area_registry import all_areas, area_of
    with caplog.at_level(logging.WARNING):
        modul(_manifest(tmp_path, agent_areas=[{"area": "home_control", "tools": ["shell_exec", "fake_tool"]}]),
              ["fake_tool"])
        assert area_of("shell_exec") == "shell"
        holders = [a["id"] for a in all_areas() if "shell_exec" in a["tools"]]
    assert holders == ["shell"]
    assert area_of("fake_tool") == "home_control"                              # das Unstrittige gilt weiter
    assert any("shell_exec" in r.getMessage() for r in caplog.records)


def test_zuordnung_zu_unbekanntem_bereich_wird_verworfen(modul, tmp_path, caplog):
    from hydrahive.agents._area_registry import area_of
    with caplog.at_level(logging.WARNING):
        modul(_manifest(tmp_path, agent_areas=[{"area": "gibt_es_nicht", "tools": ["fake_tool"]}]), ["fake_tool"])
        assert area_of("fake_tool") is None
    assert any("gibt_es_nicht" in r.getMessage() for r in caplog.records)


def test_area_of_base_und_unbekannt():
    from hydrahive.agents._area_registry import area_of
    assert area_of("find_tools") == "base" and area_of("todo_write") == "base"
    assert area_of("file_read") == "files_read"
    assert area_of("gibt_es_nicht") is None


def test_unbekanntes_tool_in_unassigned(modul, tmp_path):
    from hydrahive.agents._area_registry import unassigned
    modul(_manifest(tmp_path), ["lose_tool_eins", "lose_tool_zwei"])
    assert {"lose_tool_eins", "lose_tool_zwei"} <= set(unassigned())
    assert unassigned() == sorted(unassigned())
    assert "file_read" not in unassigned() and "find_tools" not in unassigned()


def test_kein_kern_tool_ohne_bereich():
    from hydrahive.agents._area_registry import unassigned
    assert unassigned() == []                                                  # Wächter: Test-Setup hat nur Kern-Tools


def test_mcp_tools_nie_in_unassigned(monkeypatch):
    from hydrahive.agents._area_registry import unassigned
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("x")
    monkeypatch.setitem(REGISTRY, "mcp__srv__werkzeug", Tool(name="mcp__srv__werkzeug", description="m",
                                                              schema={"type": "object"}, execute=_x))
    assert "mcp__srv__werkzeug" not in unassigned()


# ── Route ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_route_braucht_anmeldung(client):
    assert client.get("/api/agent-areas").status_code == 401


def test_route_liefert_gruppen_bereiche_base(client, auth_headers):
    r = client.get("/api/agent-areas?lang=de", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"groups", "areas", "base", "categories", "unassigned"}
    assert len(body["groups"]) == 9 and len(body["areas"]) >= 26
    assert body["groups"][0]["id"] == "files_code" and body["groups"][0]["name"] == "Dateien & Code"
    assert "find_tools" in body["base"] and "file_read" not in body["base"]
    shell = next(a for a in body["areas"] if a["id"] == "shell")
    assert shell["name"] == "Befehle ausführen" and shell["marks"] == ["risky"]
    en = client.get("/api/agent-areas?lang=en", headers=auth_headers).json()
    assert next(a for a in en["areas"] if a["id"] == "shell")["name"] == "Run commands"
    assert en["groups"][0]["name"] == "Files & code"


def test_unassigned_nur_fuer_admin(client, auth_headers, admin_headers, modul, tmp_path):
    modul(_manifest(tmp_path), ["lose_tool_route"])
    nutzer = client.get("/api/agent-areas", headers=auth_headers).json()
    admin = client.get("/api/agent-areas", headers=admin_headers).json()
    assert nutzer["unassigned"] == []                                          # sonst leer
    assert "lose_tool_route" in admin["unassigned"]
    assert "lose_tool_route" not in json.dumps({k: v for k, v in nutzer.items()})   # auch nirgends sonst


def test_route_unbekannte_sprache_ist_deutsch(client, auth_headers):
    body = client.get("/api/agent-areas?lang=xx", headers=auth_headers).json()
    assert next(a for a in body["areas"] if a["id"] == "shell")["name"] == "Befehle ausführen"


def test_plugin_tools_werden_ueber_ihre_muster_aufgeloest(monkeypatch):
    """Review #789 M2: Plugin-Tools liegen nicht in tools.REGISTRY – die Plugin-Muster aus Spec 3.2 müssen trotzdem greifen."""
    from hydrahive.agents import _area_registry
    from hydrahive.plugins import tool_bridge
    monkeypatch.setattr(tool_bridge, "all_tool_meta", lambda: [
        {"name": "plugin__git-stats__git_commits", "description": "", "category": "plugin:git-stats"},
        {"name": "plugin__http-tester__request", "description": "", "category": "plugin:http-tester"}])
    assert _area_registry.area_of("plugin__git-stats__git_commits") == "code"
    assert _area_registry.area_of("plugin__http-tester__request") == "web_open"


def test_modul_darf_aussen_tool_nicht_in_harmlosen_kernbereich(monkeypatch):
    """Review #789 S3: ein Außen-/Capability-Tool unter „Dateien lesen“ würde mit einem harmlosen Klick still mitvergeben."""
    from hydrahive.agents import _area_registry
    from hydrahive.db import _mirror_groups
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("")
    monkeypatch.setitem(REGISTRY, "fake_outward", Tool(name="fake_outward", description="x", schema={"type": "object"},
                                                       execute=_x))
    monkeypatch.setattr(_mirror_groups, "OUTWARD_TOOLS", _mirror_groups.OUTWARD_TOOLS | {"fake_outward"})
    monkeypatch.setattr(_area_registry, "_module_entries", lambda: [
        ("evil", {"area": "files_read", "tools": ["fake_outward"]}),
        ("ok", {"area": "web_open", "tools": ["fake_outward"]})])
    assert _area_registry.area_of("fake_outward") == "web_open"          # ⚠️-Bereich darf, harmloser nicht


def test_fremdes_modul_faengt_kein_kern_praefix(monkeypatch):
    """Review #790: task_* gehört dem Modul tasks. Ein gleichnamiges Präfix aus einem fremden Modul landet NICHT in
    „Aufgaben & Ideen“ (ohne Zeichen), sondern ohne Bereich – das Tool aus dem richtigen Modul schon."""
    from hydrahive.agents import _area_registry
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("")
    for name, mod in (("task_purge_all_remote", "evil"), ("task_list_fake", "tasks"), ("graph_fake", "evil")):
        monkeypatch.setitem(REGISTRY, name, Tool(name=name, description="x", schema={"type": "object"}, execute=_x,
                                                 module_id=mod))
    assert _area_registry.area_of("task_list_fake") == "tasks"
    assert _area_registry.area_of("task_purge_all_remote") is None
    assert _area_registry.area_of("graph_fake") is None
    assert {"task_purge_all_remote", "graph_fake"} <= set(_area_registry.unassigned())


def test_route_liefert_kategorie_aufloesung(client, auth_headers):
    """Review #794: Der Editor braucht, was hinter kategorie:x steckt, um „teilweise über Kategorie“ im Entwurf zu zeigen."""
    body = client.get("/api/agent-areas", headers=auth_headers).json()
    assert "files" in body["categories"] and "file_read" in body["categories"]["files"]
    assert all(isinstance(v, list) for v in body["categories"].values())
