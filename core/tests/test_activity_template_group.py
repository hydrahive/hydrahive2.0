"""Template-Gruppe eines Agenten für die Charakter-Zuordnung im Agenten-Büro (Spec agent-office.md §4.1)."""
from __future__ import annotations

from hydrahive.agents import templates as agent_templates
from hydrahive.runner._activity_link import template_group_for_agent


def test_ohne_template_fallback_specialists():
    assert template_group_for_agent({}) == "specialists"


def test_unbekanntes_template_fallback_specialists():
    assert template_group_for_agent({"template": "gibt-es-nicht"}) == "specialists"


def test_liefert_die_gruppe_des_templates():
    tpl = agent_templates.list_templates()[0]
    group = agent_templates.get(tpl["id"])["group"]
    assert template_group_for_agent({"template": tpl["id"]}) == group
