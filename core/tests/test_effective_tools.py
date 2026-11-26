"""Katalog Etappe 1, Aufgabe 1: effective_tool_names / possible_tool_names (Spec S6, docs/plans/2026-11-26-tool-skill-katalog.md).

Eine einzige Stelle für die wirksamen Tools eines Laufs. Reihenfolge fest (S6):
Config ∪ Pool → Kategorien auflösen → scope_tools (Projekt, Container) → access_filter_tools (Besitzer).
Ohne Pool und ohne Kategorien muss das exakt der bisherige Runner-Code sein (K7: classic wie heute).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

HOST_PROJEKT = {"id": "p", "mcp_server_ids": [], "allowed_plugins": []}
PLUGIN_PROJEKT = {"id": "p", "mcp_server_ids": ["m1"], "allowed_plugins": ["git-stats"]}
KAPUTT_PROJEKT = {"id": "p", "execution": {"mode": "container"}}       # Container ohne Namen → beschädigt
CONTAINER_PROJEKT = {"id": "p", "mcp_server_ids": [], "allowed_plugins": [],
                     "execution": {"mode": "container", "container": "hh-labor-probe", "workdir": "/work", "user": 1000}}

# Drei Agenten-Configs wie im Bestand (Master, Projekt-Agent, Spezialist).
AGENTEN = {
    "master": {"id": "m", "type": "master", "tools": ["shell_exec", "file_read", "web_search", "send_mail",
                                                      "ask_agent", "plugin__git-stats__git_commits", "todo_write"],
               "mcp_servers": ["m1"]},
    "projekt": {"id": "p1", "type": "project", "tools": ["file_read", "file_write", "shell_exec", "web_browser",
                                                         "plugin__git-stats__git_commits", "create_specialist"],
                "mcp_servers": []},
    "spezialist": {"id": "s1", "type": "specialist", "tools": ["file_read", "grep", "load_skill", "webmin_status"]},
}


def _alt(agent: dict, project: dict | None, username: str) -> list[str]:
    """Der bisherige Runner-Code (runner.py 137–143 vor der Änderung), wörtlich nachgebaut."""
    from hydrahive.access.tool_filter import filter_tools as access_filter_tools
    from hydrahive.runner._project_tool_scope import scope_tools
    local_tools, _ = scope_tools(project, list(agent.get("tools", [])), list(agent.get("mcp_servers", [])))
    return access_filter_tools(username, local_tools)


@pytest.mark.parametrize("name", list(AGENTEN))
@pytest.mark.parametrize("project", [None, HOST_PROJEKT, CONTAINER_PROJEKT, PLUGIN_PROJEKT, KAPUTT_PROJEKT],
                         ids=["ohne", "host", "container", "plugins", "kaputt"])
def test_classic_gleich_wie_heute(name, project):
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = AGENTEN[name]
    assert effective_tool_names(agent, username="till", project=project) == _alt(agent, project, "till")


def test_classic_gleich_wie_heute_mit_zugriffsfilter():
    """Auch mit einem Besitzer, dem Tools fehlen: Ergebnis wie der alte Code."""
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = AGENTEN["master"]
    with patch("hydrahive.access.tool_filter.tool_denied",
               side_effect=lambda u, t: "x" if t in ("shell_exec", "web_search") else None):
        got = effective_tool_names(agent, username="anna", project=None)
        assert got == _alt(agent, None, "anna")
    assert "shell_exec" not in got and "file_read" in got


def test_container_projekt_filtert_pool():
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = {"id": "a", "type": "project", "tools": ["file_read"]}
    got = effective_tool_names(agent, username="till", project=CONTAINER_PROJEKT,
                               pool=["web_browser", "send_mail", "web_search", "plugin__git-stats__git_commits"])
    assert got == ["file_read", "web_search"]                      # nur Container-Allowlist, Rest fällt raus


def test_besitzer_filter_gilt_fuer_pool():
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = {"id": "a", "type": "master", "tools": ["file_read"]}
    with patch("hydrahive.access.tool_filter.tool_denied", side_effect=lambda u, t: "web" if t == "web_browser" else None):
        got = effective_tool_names(agent, username="anna", project=None, pool=["web_browser", "web_search"])
    assert got == ["file_read", "web_search"]                      # Tool mit Capability ohne Freigabe fällt raus


def test_reihenfolge_stabil_und_ohne_duplikate():
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = {"id": "a", "type": "master", "tools": ["file_read", "grep", "file_read", "todo_write"]}
    got = effective_tool_names(agent, username="till", project=None, pool=["todo_write", "web_search", "grep", "fetch_url"])
    assert got == ["file_read", "grep", "todo_write", "web_search", "fetch_url"]      # Config, dann Pool, keine Duplikate
    assert got == effective_tool_names(agent, username="till", project=None, pool=["todo_write", "web_search", "grep", "fetch_url"])


def test_pool_none_und_leer_sind_gleich():
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = AGENTEN["spezialist"]
    base = effective_tool_names(agent, username="till", project=None)
    assert effective_tool_names(agent, username="till", project=None, pool=None) == base
    assert effective_tool_names(agent, username="till", project=None, pool=[]) == base


def test_agent_ohne_tools_feld_ergibt_leere_liste():
    from hydrahive.agents.effective_tools import effective_tool_names, possible_tool_names
    assert effective_tool_names({"id": "a"}, username="till", project=None) == []
    assert possible_tool_names({"id": "a"}) == set()


def test_eingabe_wird_nicht_veraendert():
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = {"id": "a", "tools": ["file_read", "grep"]}
    pool = ["web_search"]
    effective_tool_names(agent, username="till", project=None, pool=pool)
    assert agent["tools"] == ["file_read", "grep"] and pool == ["web_search"]


def test_moegliche_tools_fuer_aussen_einstufung():
    """D4: Gedächtnis-Einstufung nach möglicher Freigabe – ein Pool mit send_mail macht den Agenten zum Außen-Agenten."""
    from hydrahive.agents.effective_tools import possible_tool_names
    from hydrahive.db._mirror_groups import has_outward_tools
    agent = {"id": "a", "type": "project", "tools": ["file_read"]}
    assert has_outward_tools(sorted(possible_tool_names(agent))) is False
    assert has_outward_tools(sorted(possible_tool_names({**agent, "tool_pool": ["send_mail"]}))) is True


def test_moegliche_tools_ohne_projekt_und_besitzerfilter():
    """possible_tool_names ist Config ∪ Pool des Agenten OHNE Projekt-/Besitzer-Filter (Gedächtnis-Sicht, D4)."""
    from hydrahive.agents.effective_tools import possible_tool_names
    agent = {"id": "a", "tools": ["file_read", "web_browser", "send_mail", "plugin__git-stats__git_commits"]}
    assert possible_tool_names(agent) == {"file_read", "web_browser", "send_mail", "plugin__git-stats__git_commits"}


def test_kategorien_hook_loest_nur_kategorien_auf():
    """Aufgabe 4 hat resolve_categories eingehängt: Einzelne Namen bleiben, ``kategorie:<name>`` wird aufgelöst."""
    from hydrahive.agents import effective_tools as et
    got = et.resolve_categories(["file_read", "kategorie:medien", "plugin__git-stats__git_commits"])
    assert got[0] == "file_read" and got[-1] == "plugin__git-stats__git_commits"
    assert "generate_image" in got and not any(n.startswith("kategorie:") for n in got)


def test_scope_mirror_nutzt_possible_tool_names():
    """_mirror_scope stuft nach der möglichen Freigabe ein (nicht nach agent['tools'] direkt)."""
    from hydrahive.db._mirror_scope import scope_for
    sc = scope_for({"type": "project", "tools": ["file_read", "send_mail"], "knowledge_access": {"max_level": "gesundheit"}},
                   username="till", project_id="P1")
    assert sc.max_level == "normal"
    with patch("hydrahive.agents.effective_tools.possible_tool_names", return_value={"send_mail"}) as m:
        sc2 = scope_for({"type": "project", "tools": ["file_read"], "knowledge_access": {"max_level": "gesundheit"}},
                        username="till", project_id="P1")
    assert m.called and sc2.max_level == "normal"


def test_runner_nutzt_effective_tool_names():
    """Der Runner rechnet die Tool-Liste über die zentrale Funktion (Struktur-Test gegen Rückfall auf Einzelrechnung)."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src" / "hydrahive" / "runner" / "runner.py").read_text()
    assert "effective_tool_names(" in src
    assert "local_tools = access_filter_tools(" not in src


def test_agent_knowledge_nutzt_possible_tool_names():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src" / "hydrahive" / "api" / "routes" / "agent_knowledge.py").read_text()
    assert "possible_tool_names(" in src
    assert 'groups.has_outward_tools(agent.get("tools"))' not in src


def test_effective_liest_tool_pool_aus_der_config_nicht():
    """Review #781 (Security, sollte): der Pool darf nur als geprüfter Parameter wirken, nie aus dem Config-Feld."""
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = {"id": "x", "type": "project", "tools": ["file_read"], "tool_pool": ["shell_exec"]}
    with patch("hydrahive.access.tool_filter.filter_tools", side_effect=lambda u, n: list(n)):
        assert effective_tool_names(agent, username="u", project=None) == ["file_read"]


def test_doppelte_eintraege_werden_entfernt_bewusste_abweichung():
    """Einzige Abweichung vom alten Pfad: Duplikate in agent.tools fallen weg (vorher doppelt an das Modell)."""
    from hydrahive.agents.effective_tools import effective_tool_names
    agent = {"id": "x", "type": "project", "tools": ["file_read", "file_write", "file_read"]}
    with patch("hydrahive.access.tool_filter.filter_tools", side_effect=lambda u, n: list(n)):
        assert effective_tool_names(agent, username="u", project=None) == ["file_read", "file_write"]


def test_aussen_einstufung_fail_closed_bei_fehler():
    """Review #781 (Security, sollte): wirft possible_tool_names, bleibt die Gedächtnis-Stufe höchstens normal."""
    from hydrahive.db import _mirror_scope
    agent = {"id": "x", "type": "project", "tools": ["file_read"]}
    with patch("hydrahive.agents.effective_tools.possible_tool_names", side_effect=RuntimeError("DB weg")):
        assert _mirror_scope._outward(agent) is True
    assert _mirror_scope._outward(agent) is False
