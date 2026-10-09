"""Wissensräume E2a: Gruppen ohne Buddy-Chats, Außenwirkung begrenzt die Stufe (knowledge-spaces.md §2.2)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from hydrahive.agents._knowledge_access import normalize
from hydrahive.agents._validation import AgentValidationError
from hydrahive.db import _mirror_groups as groups
from hydrahive.db._mirror_levels import hidden_tools
from hydrahive.db._mirror_scope import Scope, scope_for, where


# ── Außenwirkung ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tool", ["shell_exec", "discord_post", "send_mail", "web_browser", "fetch_url"])
def test_aussenwirkung_begrenzt_projekt_agent_auf_normal(tool):
    a = {"type": "project", "tools": [tool], "knowledge_access": {"max_level": "gesundheit"}}
    assert scope_for(a, username="t", project_id="P").max_level == "normal"


def test_lesende_werkzeuge_sind_keine_aussenwirkung():
    a = {"type": "project", "tools": ["discord_read", "file_read", "datamining_search"],
         "knowledge_access": {"max_level": "privat"}}
    assert scope_for(a, username="t", project_id="P").max_level == "privat"


def test_buddy_behaelt_seine_stufe_trotz_shell():
    assert scope_for({"type": "master", "tools": ["shell_exec"]}, username="t", project_id=None).max_level == "gesundheit"


# ── Gruppen: wer gehört dazu? ─────────────────────────────────────────────────

def _users(uid):
    return {"u-till": {"username": "till"}, "u-bibi": {"username": "bibi"}, "u-admin": {"username": "admin"}}.get(uid)


def test_gruppenmitglieder_ohne_eigenen_nutzer_sortiert():
    with patch("hydrahive.access.store.members_of", return_value=["u-till", "u-bibi", "u-admin", "u-weg"]), \
         patch("hydrahive.api.middleware.users.get_by_id", side_effect=_users):
        assert groups.group_usernames(["G"], exclude="till") == ("admin", "bibi")
    assert groups.group_usernames([], exclude="till") == ()


def test_scope_for_traegt_gruppen_und_master_ein():
    a = {"type": "project", "knowledge_access": {"groups": ["G"]}}
    with patch.object(groups, "group_usernames", return_value=("bibi",)), \
         patch.object(groups, "master_agent_ids", return_value=("buddy-1",)):
        sc = scope_for(a, username="till", project_id="P")
    assert sc.group_users == ("bibi",) and sc.master_agents == ("buddy-1",)


def test_ohne_gruppen_keine_master_abfrage():
    with patch.object(groups, "master_agent_ids", side_effect=AssertionError("nicht nötig")):
        assert scope_for({"type": "project"}, username="t", project_id="P").group_users == ()


# ── Gruppen: was sieht man? (SQL) ─────────────────────────────────────────────

def test_gruppenteil_nur_projekt_sitzungen_ohne_buddys_hoechstens_normal():
    sc = Scope(username="till", projects=("P1",), max_level="privat", group_users=("bibi",), master_agents=("m1",))
    conds, params, _ = where(sc, 1)
    sql = conds[0]
    assert sql.startswith("((events.username = $1 AND events.project_id = ANY($2::text[])) OR (")
    assert "events.username = ANY($3::text[])" in sql and "events.project_id IS NOT NULL" in sql
    assert "events.agent_id IS NOT NULL" in sql and "events.agent_id <> ALL($4::text[])" in sql
    assert "g.tool_name = ANY($5::text[])" in sql
    assert params[2:5] == [["bibi"], ["m1"], hidden_tools("normal")]
    assert params[-1] == hidden_tools("privat")       # Stufen-Sperre des Agenten gilt zusätzlich für alles


def test_projekt_agent_ohne_projekt_sieht_nur_gruppe():
    conds, params, _ = where(Scope(username="till", projects=(), group_users=("bibi",), master_agents=()), 1)
    assert conds[0].startswith("((FALSE) OR (") and params[0] == ["bibi"]


def test_ohne_gruppe_und_ohne_projekt_nichts():
    assert where(Scope(username="till", projects=()), 1) == (["FALSE"], [], 1)


def test_buddy_mit_gruppe_sieht_eigenes_alles_plus_gruppenprojekte():
    sc = Scope(username="till", scope="user", max_level="gesundheit", group_users=("bibi",), master_agents=("m1",))
    conds, params, _ = where(sc, 1)
    assert conds[0].startswith("((events.username = $1) OR (") and len(conds) == 1   # keine Stufen-Sperre fürs Eigene
    assert params[0] == "till"


# ── Prüfung der Einstellung ───────────────────────────────────────────────────

def test_groups_wird_geprueft():
    with patch("hydrahive.access.store.get_group", side_effect=lambda g: {"id": g} if g == "G" else None):
        assert normalize({"groups": ["G", " G "]}) == {"groups": ["G"]}
        with pytest.raises(AgentValidationError):
            normalize({"groups": ["NOPE"]})
    with pytest.raises(AgentValidationError):
        normalize({"groups": "G"})


def test_master_agent_ids_nur_master_sortiert():
    agents = [{"id": "z-buddy", "type": "master"}, {"id": "p1", "type": "project"},
              {"id": "a-assist", "type": "master"}, {"id": "s1", "type": "specialist"}]
    with patch("hydrahive.agents._config_utils.list_all", return_value=agents):
        assert groups.master_agent_ids() == ("a-assist", "z-buddy")
