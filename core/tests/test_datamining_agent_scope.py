"""Datamining-Zugriff je Agent (docs/specs/datamining-access.md, Task b17f9e38 E0).

Vorher: datamining_* filterten nur nach Nutzer – jeder Agent sah das ganze Gedächtnis des Nutzers,
auch fremde Projekte und Gesundheits-Sitzungen. Jetzt: Projekt-Agenten nur ihr Projekt (+ vom Admin
freigegebene), Buddys alles des Nutzers, sensible Sitzungen nur mit Freigabe.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from hydrahive.db._mirror_levels import hidden_tools
from hydrahive.db._mirror_scope import Scope, scope_for, where

NOT_NORMAL = hidden_tools("normal")


# ── Regeln: welche Sicht hat ein Agent? ───────────────────────────────────────

def test_projekt_agent_sieht_nur_sein_projekt():
    sc = scope_for({"type": "project"}, username="till", project_id="P1")
    assert sc == Scope(username="till", scope="project", projects=("P1",), max_level="normal")


def test_spezialist_ebenso_und_ohne_projekt_gar_nichts():
    assert scope_for({"type": "specialist"}, username="till", project_id="P1").projects == ("P1",)
    conds, params, _ = where(scope_for({"type": "specialist"}, username="till", project_id=None), 1)
    assert conds == ["FALSE"] and params == []


def test_buddy_sieht_alles_des_nutzers_auch_sensibles():
    sc = scope_for({"type": "master", "is_buddy": True}, username="till", project_id=None)
    assert sc.scope == "user" and sc.max_level == "gesundheit"


def test_admin_freigabe_zusaetzlicher_projekte_und_sensibel():
    agent = {"type": "project", "knowledge_access": {"projects": ["P2", "P1"], "sensitive": True}}
    sc = scope_for(agent, username="till", project_id="P1")
    assert sc.projects == ("P1", "P2") and sc.max_level == "gesundheit"


def test_unbekannter_agent_und_kaputter_wert_sind_streng():
    assert scope_for(None, username="till", project_id="P1").scope == "project"
    sc = scope_for({"type": "project", "knowledge_access": {"scope": "alles"}}, username="till", project_id="P1")
    assert sc.scope == "project"


def test_ohne_nutzer_nie_treffer():
    conds, _, _ = where(Scope(username="", scope="user", max_level="gesundheit"), 1)
    assert conds == ["FALSE"]


def test_werte_nur_als_parameter_nie_im_sql():
    evil = "P1') OR 1=1 --"
    conds, params, nxt = where(Scope(username="x' OR '1'='1", projects=(evil,)), 5)
    sql = " AND ".join(conds)
    assert evil not in sql and "x' OR" not in sql
    assert params[0] == "x' OR '1'='1" and params[1] == [evil] and NOT_NORMAL == params[2]
    assert "$5" in sql and "$6" in sql and "$7" in sql and nxt == 8


# ── Werkzeuge reichen die Sicht des Agenten weiter ───────────────────────────

def _ctx(agent_id="a1", project_id="P1"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id=agent_id, user_id="till", workspace=Path("/tmp"),
                       project_id=project_id)


@pytest.mark.parametrize("tool_name,fn,args", [
    ("datamining_search", "search_events", {"query": "x"}),
    ("datamining_semantic", "search_events", {"query": "x"}),
    ("datamining_timeline", "list_sessions", {}),
    ("datamining_today", "list_sessions", {}),
])
def test_alle_vier_werkzeuge_uebergeben_den_scope(tool_name, fn, args):
    from hydrahive.tools import datamining
    tool = {t.name: t for t in (datamining.TOOL_SEARCH, datamining.TOOL_SEMANTIC,
                                datamining.TOOL_TIMELINE, datamining.TOOL_TODAY)}[tool_name]
    seen: dict = {}

    async def fake(*a, **kw):
        seen.update(kw)
        return []

    with patch(f"hydrahive.db.mirror_query.{fn}", side_effect=fake), \
         patch("hydrahive.agents.config.get", return_value={"type": "project"}):
        asyncio.run(tool.execute(args, _ctx()))
    assert seen["scope"] == Scope(username="till", scope="project", projects=("P1",), max_level="normal")


def test_sensibel_sperre_bestimmt_die_sitzungen_einmal_statt_je_treffer():
    """Gemessen 09.10. (.2): NOT EXISTS je Treffer 2,2 s bei häufigen Wörtern, Liste einmal 0,08 s – gleiche Treffer."""
    conds, params, _ = where(Scope(username="till", projects=("P1",)), 1)
    sensible = [c for c in conds if "s.tool_name" in c]
    assert len(sensible) == 1
    assert "<> ALL(ARRAY(SELECT DISTINCT s.session_id FROM events s WHERE s.tool_name = ANY($3::text[])))" in sensible[0]
    assert "NOT EXISTS" not in sensible[0] and "s.session_id = events.session_id" not in sensible[0]
    assert params[2] == NOT_NORMAL


def test_mit_freigabe_keine_sensibel_sperre():
    conds, params, _ = where(Scope(username="till", projects=("P1",), max_level="gesundheit"), 1)
    assert not any("s.tool_name" in c for c in conds) and len(params) == 2
