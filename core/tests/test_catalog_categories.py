"""Katalog Etappe 3, Aufgabe 4: Kategorien-Freigabe (Spec S2, K12, K15; docs/plans/2026-11-26-tool-skill-katalog.md).

Eine Kategorie (``kategorie:<name>``) gibt nur Tools frei, die im Kern fest zugeordnet sind oder die ein Admin bestätigt hat.
Nie frei werden Plugin- und MCP-Tools, Tools mit Capability, AUTHORING_TOOLS, ask_agent und Außen-Tools (OUTWARD_TOOLS).
"""
from __future__ import annotations

import pytest

from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok("x")


def _tool(name: str, *, category: str = "media", module_id: str = "") -> Tool:
    return Tool(name=name, description=f"Testwerkzeug {name}", schema={"type": "object", "properties": {}},
                execute=_noop, category=category, module_id=module_id)


def _agent(*tools: str) -> dict:
    return {"id": "a1", "type": "master", "tools": list(tools)}


def test_migration_067_tabelle_da(mod_env):
    from hydrahive.db.connection import db
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tool_category_approvals)")}
    assert {"category", "tool", "approved_by", "approved_at"} <= cols


def test_kategorie_loest_auf_und_bleibt_stabil(mod_env):
    from hydrahive.catalog.categories import resolve_categories
    got = resolve_categories(["todo_write", "kategorie:files", "file_read"])
    assert got[0] == "todo_write" and "file_write" in got and "file_patch" in got
    assert got.count("file_read") == 1                                  # Duplikate raus
    assert resolve_categories(["file_read", "web_search"]) == ["file_read", "web_search"]   # ohne Kategorie unverändert
    assert resolve_categories(["kategorie:gibt-es-nicht"]) == []        # unbekannt → nichts frei


def test_kategorie_in_effective_und_possible_tool_names(mod_env):
    from hydrahive.agents.effective_tools import effective_tool_names, possible_tool_names
    agent = _agent("kategorie:files", "todo_write")
    assert {"file_read", "file_write", "todo_write"} <= set(effective_tool_names(agent, username="till", project=None))
    assert {"file_read", "file_write", "todo_write"} <= possible_tool_names(agent)
    assert not any(n.startswith("kategorie:") for n in possible_tool_names(agent))


def test_kategorie_mit_aussen_tool_macht_agent_nach_aussen(mod_env, monkeypatch):
    """K15: Kategorien lösen sich in possible_tool_names auf; ein Außen-Tool kann in keiner Kategorie stehen,
    daher bleibt die Gedächtnis-Stufe höchstens normal (has_outward_tools bleibt False)."""
    from hydrahive.agents.effective_tools import possible_tool_names
    from hydrahive.catalog import categories
    from hydrahive.db._mirror_groups import OUTWARD_TOOLS, has_outward_tools
    # 1) Das feste Mapping enthält kein Außen-Tool.
    for cat, names in categories.CATEGORY_MAP.items():
        assert not set(names) & OUTWARD_TOOLS, f"Kategorie {cat} enthält ein Außen-Tool"
    # 2) Selbst ein (fälschlich) eingetragenes Außen-Tool würde nicht frei.
    evil = {**categories.CATEGORY_MAP, "web": (*categories.CATEGORY_MAP["web"], "fetch_url", "send_mail", "shell_exec")}
    monkeypatch.setattr(categories, "CATEGORY_MAP", evil)
    possible = possible_tool_names(_agent(*[f"kategorie:{c}" for c in evil]))
    assert not possible & OUTWARD_TOOLS
    assert has_outward_tools(sorted(possible)) is False


def test_nachtraeglich_zugeordnet_nicht_frei_bis_bestaetigt(mod_env, monkeypatch):
    """K12: Ein Modul-Tool, das nachträglich in eine Kategorie kommt, ist nicht frei, bis ein Admin es bestätigt."""
    from hydrahive.catalog.categories import approve, resolve_categories
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "mod_bildchen", _tool("mod_bildchen", module_id="mod1"))
    assert "mod_bildchen" not in resolve_categories(["kategorie:media"])
    with pytest.raises(PermissionError):
        approve("media", "mod_bildchen", "testuser")                  # Nicht-Admin darf nicht
    assert "mod_bildchen" not in resolve_categories(["kategorie:media"])
    approve("media", "mod_bildchen", "admin")
    assert "mod_bildchen" in resolve_categories(["kategorie:media"])
    assert "mod_bildchen" not in resolve_categories(["kategorie:files"])      # Bestätigung gilt nur für diese Kategorie


def test_bestaetigung_gilt_nicht_fuer_andere_kategorie_des_tools(mod_env, monkeypatch):
    from hydrahive.catalog.categories import approve, resolve_categories
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "mod_x", _tool("mod_x", category="files", module_id="mod1"))
    with pytest.raises(ValueError):
        approve("media", "mod_x", "admin")                            # Tool gehört gar nicht in „medien“
    assert "mod_x" not in resolve_categories(["kategorie:media"])


def test_plugin_mit_kategorie_nicht_frei(mod_env, monkeypatch):
    """K12: Ein Plugin mit category: media ist über die Kategorie nicht frei, auch nicht nach einer Bestätigung."""
    from hydrahive.catalog.categories import approve, resolve_categories
    from hydrahive.db.connection import db
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "plugin__bild__mal", _tool("plugin__bild__mal"))
    assert "plugin__bild__mal" not in resolve_categories(["kategorie:media"])
    with pytest.raises(ValueError):
        approve("media", "plugin__bild__mal", "admin")
    with db() as conn:                                                  # sogar eine direkt eingetragene Zeile hilft nicht
        conn.execute("INSERT OR REPLACE INTO tool_category_approvals(category, tool, approved_by, approved_at) "
                     "VALUES ('media', 'plugin__bild__mal', 'admin', 'x')")
    assert "plugin__bild__mal" not in resolve_categories(["kategorie:media"])


@pytest.mark.parametrize("gruppe, name, module_id", [
    ("plugin", "plugin__x__tool", ""),
    ("mcp", "mcp__srv__tool", ""),
    ("authoring", "create_specialist", ""),
    ("ask_agent", "ask_agent", ""),
    ("aussen", "send_mail", ""),
    ("capability", "mod_mit_capability", "mod2"),
])
def test_ausschluesse_nie_ueber_kategorie(mod_env, monkeypatch, gruppe, name, module_id):
    """S2: je Gruppe – weder über das feste Mapping noch über eine (direkt in die DB geschriebene) Bestätigung frei."""
    from hydrahive.catalog import categories
    from hydrahive.db.connection import db
    from hydrahive.tools import REGISTRY
    if name not in REGISTRY:
        monkeypatch.setitem(REGISTRY, name, _tool(name, module_id=module_id))
    if gruppe == "capability":
        monkeypatch.setattr(categories, "_capability_for", lambda n, mid: "module.mod2" if n == name else None)
    monkeypatch.setattr(categories, "CATEGORY_MAP", {**categories.CATEGORY_MAP, "media": (*categories.CATEGORY_MAP["media"], name)})
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO tool_category_approvals(category, tool, approved_by, approved_at) "
                     "VALUES ('media', ?, 'admin', 'x')", (name,))
    assert name not in categories.resolve_categories(["kategorie:media"])
    with pytest.raises(ValueError):
        categories.approve("media", name, "admin")


def test_explizit_genanntes_tool_bleibt_wie_heute(mod_env):
    """Nur ``kategorie:…`` wird aufgelöst; ein einzeln eingetragenes Tool (auch Plugin) läuft wie bisher durch."""
    from hydrahive.catalog.categories import resolve_categories
    names = ["plugin__git-stats__git_commits", "shell_exec", "ask_agent", "file_read"]
    assert resolve_categories(names) == names


def test_fehler_in_db_gibt_nichts_frei(mod_env, monkeypatch):
    """Fail-closed: Ist die Bestätigungs-Tabelle nicht lesbar, wird nur das feste Mapping aufgelöst."""
    from hydrahive.catalog import categories
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "mod_y", _tool("mod_y", module_id="mod1"))
    monkeypatch.setattr(categories, "_approved", lambda category: (_ for _ in ()).throw(RuntimeError("db kaputt")))
    got = categories.resolve_categories(["kategorie:media"])
    assert "mod_y" not in got and "generate_image" in got



def test_kategorien_heissen_wie_tool_category():
    """Fängt (Buddy-Review #784): deutsche Kategorie-Namen ↔ englische Tool.category → approve() wirkte für 7 von 10
    Kategorien nie. Jede Kategorie (außer der Sonderfall ``skills``) muss der Tool.category ihrer Tools entsprechen."""
    from hydrahive.catalog.categories import CATEGORY_LABELS, CATEGORY_MAP
    from hydrahive.tools import REGISTRY
    for cat, names in CATEGORY_MAP.items():
        if cat == "skills":
            continue
        cats = {REGISTRY[n].category for n in names if n in REGISTRY}
        assert cats == {cat}, f"Kategorie {cat}: Tools liegen in {cats}"
    assert set(CATEGORY_LABELS) == set(CATEGORY_MAP), "jede Kategorie braucht eine deutsche Beschreibung"


def test_approve_wirkt_fuer_eine_feste_kategorie(monkeypatch, client):
    """Eine bestätigte Zuordnung muss auch in einer Kategorie mit festem Mapping wirken (z. B. files)."""
    from hydrahive.catalog import categories
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "mod_datei_extra", _tool("mod_datei_extra", category="files", module_id="mod1"))
    monkeypatch.setattr(categories, "_capability_for", lambda n, m: None)
    monkeypatch.setattr("hydrahive.api.middleware.users.get_by_username", lambda u: {"role": "admin"})
    assert "mod_datei_extra" not in categories.resolve_categories(["kategorie:files"])
    categories.approve("files", "mod_datei_extra", "admin")
    assert "mod_datei_extra" in categories.resolve_categories(["kategorie:files"])



@pytest.mark.parametrize("kategorie,tool", [("system", "webmin_call"), ("catalog", "run_tool"), ("catalog", "find_tools")])
def test_approve_nur_fuer_kategorien_aus_dem_mapping(monkeypatch, client, kategorie, tool):
    """Fängt (Review #784, sollte): approve() akzeptierte jede Tool.category – webmin_call über kategorie:system."""
    from hydrahive.catalog import categories
    from hydrahive.tools import REGISTRY
    if tool not in REGISTRY:
        monkeypatch.setitem(REGISTRY, tool, _tool(tool, category=kategorie))
    monkeypatch.setattr(categories, "_capability_for", lambda n, m: None)
    monkeypatch.setattr("hydrahive.api.middleware.users.get_by_username", lambda u: {"role": "admin"})
    with pytest.raises(ValueError):
        categories.approve(kategorie, tool, "admin")
    assert categories.resolve_categories([f"kategorie:{kategorie}"]) == []


def test_alt_eintrag_ausserhalb_des_mappings_wirkt_nie(monkeypatch, client):
    """Auch eine schon in der Tabelle stehende Zeile für eine fremde Kategorie gibt nichts frei."""
    from hydrahive.catalog import categories
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO tool_category_approvals(category, tool, approved_by, approved_at) "
                     "VALUES ('system', 'webmin_call', 'admin', 'x')")
    assert categories.resolve_categories(["kategorie:system"]) == []


def test_fehlende_tabelle_warnt_nur_einmal(monkeypatch, caplog):
    """Fängt (Review #784, sollte): bei fehlender Tabelle je Aufruf und Kategorie ein WARNING mit Traceback."""
    import logging
    from hydrahive.catalog import categories
    monkeypatch.setattr(categories, "_WARNED", False)
    monkeypatch.setattr(categories, "_approved", lambda c: (_ for _ in ()).throw(RuntimeError("no such table")))
    with caplog.at_level(logging.WARNING, logger="hydrahive.catalog.categories"):
        for _ in range(5):
            categories.resolve_categories(["kategorie:files", "kategorie:media"])
    warnungen = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnungen) == 1 and warnungen[0].exc_info is None
    assert "file_read" in categories.resolve_categories(["kategorie:files"])          # fail-closed: festes Mapping gilt
