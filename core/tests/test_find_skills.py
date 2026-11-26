"""Katalog Etappe 3, Aufgabe 4: find_skills (Spec S7, K6) – nur Skills, die dem Agenten gehören, nie fremde."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.tools.base import ToolContext


def _ctx(tmp_path: Path, *, project_id: str | None = None) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id="anna", workspace=tmp_path, project_id=project_id)


def _skill(scope, owner, name, description, when):
    from hydrahive.skills.loader import save_skill
    from hydrahive.skills.models import Skill
    ok, err = save_skill(Skill(name=name, description=description, when_to_use=when,
                               body=f"GEHEIMER-BODY-{name}", scope=scope, owner=owner))
    assert ok, err


def _run(tmp_path, monkeypatch, query, *, agent=None, project_id=None, **extra):
    from hydrahive.tools import find_skills
    monkeypatch.setattr(find_skills, "_agent_for", lambda ctx: agent if agent is not None else
                        {"id": "a1", "owner": "anna", "disabled_skills": []})
    return asyncio.run(find_skills.TOOL.execute({"query": query, **extra}, _ctx(tmp_path, project_id=project_id)))


def test_find_skills_keine_fremden_skills(mod_env, monkeypatch):
    """S7: Skills anderer Nutzer, anderer Projekte und anderer Agenten tauchen weder mit Namen noch mit Text auf."""
    _skill("user", "anna", "annas-rezepte", "Rezepte für Kuchen", "wenn Kuchen gebacken wird")
    _skill("user", "bert", "berts-kuchen-geheimnis", "Geheimes Kuchenrezept von Bert", "wenn Kuchen gebacken wird")
    _skill("project", "p-fremd", "fremdes-projekt-kuchen", "Kuchen im fremden Projekt", "Kuchen")
    _skill("project", "p1", "eigenes-projekt-kuchen", "Kuchen im eigenen Projekt", "Kuchen")
    _skill("agent", "a-fremd", "fremder-agent-kuchen", "Kuchen eines anderen Agenten", "Kuchen")
    res = _run(mod_env, monkeypatch, "Kuchen backen", project_id="p1")
    assert res.success, res.error
    names = [r["name"] for r in res.output["results"]]
    assert {"annas-rezepte", "eigenes-projekt-kuchen"} <= set(names)
    assert not set(names) & {"berts-kuchen-geheimnis", "fremdes-projekt-kuchen", "fremder-agent-kuchen"}
    import json
    blob = json.dumps(res.output, ensure_ascii=False)
    assert "Bert" not in blob and "fremden Projekt" not in blob and "GEHEIMER-BODY" not in blob   # auch kein Body


def test_find_skills_beachtet_abgeschaltete_skills(mod_env, monkeypatch):
    _skill("user", "anna", "aus-geschaltet", "Wird nicht angeboten", "Zaubertränke")
    res = _run(mod_env, monkeypatch, "Zaubertränke", agent={"id": "a1", "owner": "anna", "disabled_skills": ["aus-geschaltet"]})
    assert res.success and res.output["results"] == []


def test_find_skills_ohne_agent_nichts(mod_env, monkeypatch):
    from hydrahive.tools import find_skills
    monkeypatch.setattr(find_skills, "_agent_for", lambda ctx: None)
    res = asyncio.run(find_skills.TOOL.execute({"query": "debugging"}, _ctx(mod_env)))
    assert res.success and res.output["results"] == []                    # fail-closed, kein Fehlertext mit Inhalt


def test_find_skills_leere_anfrage(mod_env, monkeypatch):
    res = _run(mod_env, monkeypatch, "   ")
    assert not res.success and "Suchbegriff" in (res.error or "")


def test_skill_top3_fuer_fuenf_anfragen(mod_env, monkeypatch):
    """K6: Fünf Alltagsanfragen gegen die mitgelieferten System-Skills, je ein erwarteter Skill unter den ersten 3."""
    from hydrahive.skills.loader import install_system_defaults
    install_system_defaults()
    paare = [
        ("Fehler im Code suchen", "debugging"),
        ("Code prüfen lassen", "code-review"),
        ("Änderungen committen und pushen", "git-workflow"),
        ("Dokumentation schreiben", "docs"),
        ("PDF lesen und auswerten", "document-reading"),
    ]
    daneben = []
    for anfrage, erwartet in paare:
        res = _run(mod_env, monkeypatch, anfrage, limit=3)
        names = [r["name"] for r in res.output["results"]]
        if erwartet not in names:
            daneben.append((anfrage, erwartet, names))
    assert not daneben, daneben


def test_find_skills_in_registry_aber_in_keiner_default_liste():
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    from hydrahive.api.routes import agents
    from hydrahive.tools import REGISTRY
    assert "find_skills" in REGISTRY
    assert "find_skills" in agents._HIDDEN_IN_EDITOR
    for typ, tools in DEFAULT_TOOLS.items():
        assert "find_skills" not in tools, f"find_skills in DEFAULT_TOOLS[{typ}]"


def test_skills_stehen_nie_im_tool_katalog(mod_env):
    """Skills liegen nicht im globalen Tool-Speicher (der gehört keinem Nutzer): kein Leck über find_tools."""
    from hydrahive.catalog import _store
    from hydrahive.catalog.index import rebuild_tool_index
    _skill("user", "anna", "annas-geheimer-skill", "Ganz privat", "privat")
    rebuild_tool_index()
    assert not [e for e in _store.get_store().entries() if e.kind == "skill"]
