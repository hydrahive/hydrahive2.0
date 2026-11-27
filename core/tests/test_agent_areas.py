"""Agenten-Bereiche, Aufgabe 1 (AB1): das feste Bereichs-Verzeichnis im Kern (docs/specs/agent-bereiche.md 3.1/3.2).

Bereiche sind nur eine Sicht auf ``agent.tools`` (E1): Sie ordnen Tool-Namen den 28 Schaltern zu, mehr nicht.
"""
from __future__ import annotations

import pytest


def test_26_bereiche_9_gruppen():
    from hydrahive.agents.areas import CORE_AREAS, GROUPS
    assert len(CORE_AREAS) == 28 and len(GROUPS) == 9
    assert {a.group for a in CORE_AREAS} == set(GROUPS)
    for g in GROUPS:
        n = sum(1 for a in CORE_AREAS if a.group == g)
        assert 1 <= n <= 4, f"Gruppe {g} hat {n} Bereiche (Regel 4: höchstens 4)"
    assert GROUPS == ("files_code", "internet", "organize", "creative", "team", "post", "home", "private", "server")


def test_ids_wie_im_plan_und_eindeutig():
    from hydrahive.agents.areas import CORE_AREAS
    ids = [a.id for a in CORE_AREAS]
    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "files_read", "files_write", "code", "web_search", "web_open", "memory", "tasks", "tickets", "diagrams", "media",
        "atelier", "books", "delegate", "helpers", "mail_read", "mail_write", "home_view", "home_control", "downloads",
        "health", "finance", "legal", "shell", "server_admin", "game_server", "security_research", "discord_read",
        "discord_write"}


def test_texte_de_en_wörtlich_aus_der_spec():
    from hydrahive.agents.areas import CORE_AREAS
    by_id = {a.id: a for a in CORE_AREAS}
    for a in CORE_AREAS:
        assert set(a.name) == {"de", "en"} and set(a.sentence) == {"de", "en"}, a.id
        assert all(v.strip() for v in (*a.name.values(), *a.sentence.values())), a.id
    assert by_id["files_read"].name["de"] == "Dateien lesen"
    assert by_id["files_read"].sentence["de"] == "Dateien und PDFs im Projekt lesen"
    assert by_id["helpers"].name["de"] == "Helfer anlegen"
    assert by_id["home_control"].sentence["de"] == "Geräte im Haus schalten"
    assert by_id["shell"].sentence["de"] == "Programme und Befehle direkt auf dem Server starten"
    assert by_id["memory"].name["de"] == "Gedächtnis"
    assert by_id["game_server"].name["de"] == "Spiele-Server"


def test_markierungen_wie_spec():
    from hydrahive.agents.areas import CORE_AREAS
    marks = {a.id: set(a.marks) for a in CORE_AREAS}
    for i in ("home_control", "shell", "files_write", "mail_write", "web_open", "helpers", "downloads", "server_admin",
              "game_server", "security_research", "discord_write"):
        assert "risky" in marks[i], i
    for i in ("health", "memory", "mail_read", "mail_write", "finance", "legal"):
        assert "private" in marks[i], i
    for i in ("web_search", "media", "delegate"):
        assert "costly" in marks[i], i
    assert marks["files_read"] == set() and marks["tasks"] == set() and marks["home_view"] == set()
    assert marks["mail_write"] == {"risky", "private"}                       # ⚠️ 🔒
    for m in marks.values():
        assert m <= {"risky", "private", "costly"}


def test_jedes_kern_tool_genau_einmal():
    """Wächter (AB1): Jedes Tool in REGISTRY liegt in genau einem Bereich ODER in BASE_TOOLS – nie beides, nie keins."""
    from hydrahive.agents.areas import BASE_TOOLS, CORE_AREAS, tools_of
    from hydrahive.tools import REGISTRY
    registered = sorted(REGISTRY)
    problems = []
    for name in registered:
        hits = [a.id for a in CORE_AREAS if name in tools_of(a, registered)]
        in_base = name in BASE_TOOLS
        if len(hits) + int(in_base) != 1:
            problems.append((name, hits, in_base))
    assert not problems, f"Tool ohne oder mit mehreren Bereichen: {problems}"


def test_base_tools_wie_plan():
    from hydrahive.agents.areas import BASE_TOOLS
    assert BASE_TOOLS == frozenset({
        "list_skills", "load_skill", "help_search", "help_read", "error_report_prepare", "list_prompts", "get_prompt",
        "save_prompt", "todo_write", "find_tools", "find_skills", "run_tool"})


def test_bekannte_zuordnungen():
    from hydrahive.agents.areas import CORE_AREAS, tools_of
    from hydrahive.tools import REGISTRY
    reg = sorted(REGISTRY)
    by_id = {a.id: a for a in CORE_AREAS}
    assert tools_of(by_id["files_read"], reg) == ["file_read", "read_document"]
    assert tools_of(by_id["files_write"], reg) == ["file_patch", "file_write"]
    assert tools_of(by_id["shell"], reg) == ["shell_exec"]
    # ask_agent steht nur mit konfiguriertem AgentLink in REGISTRY: der Bereich kennt ihn trotzdem (Zuordnung, nicht Bestand)
    assert by_id["delegate"].tools == ("ask_agent",)
    assert tools_of(by_id["delegate"], [*reg, "ask_agent"]) == ["ask_agent"]
    assert "create_specialist" in tools_of(by_id["helpers"], reg) and "list_projects" in tools_of(by_id["helpers"], reg)
    assert set(tools_of(by_id["code"], reg)) >= {"graph_query", "graph_refresh"}
    assert set(tools_of(by_id["memory"], reg)) >= {"read_memory", "write_memory", "datamining_search"}
    assert set(tools_of(by_id["media"], reg)) >= {"generate_image", "analyze_image", "transcribe_audio"}


def test_muster_nur_praefix():
    from hydrahive.agents.areas import Area, tools_of
    a = Area(id="tt", group="files_code", name={"de": "x", "en": "x"}, sentence={"de": "x", "en": "x"}, marks=(),
             tools=("graph_*", "exakt"))
    assert tools_of(a, ["graph_b", "graph_a", "graphviz", "exakt", "exakt2", "andere"]) == ["exakt", "graph_a", "graph_b"]
    assert tools_of(a, []) == []                                              # nicht registriert → nicht dabei


def test_stern_mitten_im_namen_ist_verboten():
    from hydrahive.agents.areas import Area, check_pattern
    for kaputt in ("gr*ph", "*graph", "graph_*_x", "**", "a**"):
        with pytest.raises(ValueError):
            check_pattern(kaputt)
    check_pattern("graph_*")
    check_pattern("exakt_name")
    with pytest.raises(ValueError):
        Area(id="tt", group="files_code", name={"de": "x", "en": "x"}, sentence={"de": "x", "en": "x"}, marks=(),
             tools=("gr*ph",))


def test_marken_und_gruppen_werden_geprueft():
    from hydrahive.agents.areas import Area
    base = dict(name={"de": "x", "en": "x"}, sentence={"de": "x", "en": "x"})
    with pytest.raises(ValueError):
        Area(id="tt", group="gibt-es-nicht", marks=(), tools=(), **base)
    with pytest.raises(ValueError):
        Area(id="tt", group="internet", marks=("gefaehrlich",), tools=(), **base)
    with pytest.raises(ValueError):
        Area(id="T-x", group="internet", marks=(), tools=(), **base)          # id nur a-z_


def test_datei_unter_200_zeilen_plus_toleranz():
    from pathlib import Path
    import hydrahive.agents.areas as m
    assert len(Path(m.__file__).read_text().splitlines()) <= 260              # Daten-Datei: Tabelle der 28 Bereiche


def test_discord_tools_zugeordnet_auch_wenn_discord_aus():
    """CI läuft mit HH_DISCORD_ENABLED: alle discord_*-Tools (OPTIONAL_TOOLS) müssen einen Bereich haben, unabhängig vom Setup."""
    from hydrahive.agents.areas import BASE_TOOLS, CORE_AREAS, tools_of
    from hydrahive.tools import OPTIONAL_TOOLS
    discord = sorted(n for n in OPTIONAL_TOOLS if n.startswith("discord_"))
    assert len(discord) == 11
    for name in discord:
        hits = [a.id for a in CORE_AREAS if name in tools_of(a, discord)]
        assert len(hits) == 1 and name not in BASE_TOOLS, (name, hits)
    by_id = {a.id: a for a in CORE_AREAS}
    assert tools_of(by_id["discord_read"], discord) == ["discord_channels", "discord_read"]


def test_waechter_auch_fuer_bedingte_kern_tools(monkeypatch):
    """Review #789 M3: Die Tests laufen ohne AgentLink/Discord – der Wächter muss auch die Tools prüfen, die erst mit diesen
    Einstellungen registriert werden (ask_agent, discord_*). Dafür die Registry mit beiden Schaltern neu bauen."""
    from hydrahive import tools as tools_pkg
    from hydrahive.agents.areas import BASE_TOOLS, CORE_AREAS, tools_of
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(settings, "discord_enabled", True, raising=False)
    full = sorted(tools_pkg._build_registry())
    assert "ask_agent" in full and "discord_post" in full
    problems = [(n, hits) for n in full
                if len(hits := [a.id for a in CORE_AREAS if n in tools_of(a, full)]) + int(n in BASE_TOOLS) != 1]
    assert not problems, f"Kern-Tool ohne oder mit mehreren Bereichen: {problems}"
