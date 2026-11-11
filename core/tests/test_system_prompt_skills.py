"""Skills-Abschnitt im System-Prompt: Tabelle der verfügbaren Skills mit neutralem Ladehinweis.

Die frühere 1-%-Regel („Wenn auch nur 1% Chance besteht … lade ihn zuerst") wurde am 11.11.2026 nach dem
Vereinfachungs-Check entfernt: gleiche Erfolgsquote, weniger unnötig geladene Skills.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hydrahive.runner.system_prompt import compose


def _stable(skills):
    stable, _volatile, _summary = compose(
        "BASE", extra_system=None, workspace=Path("/tmp/ws"), summary=None,
        skills=skills, longterm_memory=False, tool_schemas=[], allowed_tools=[],
    )
    return stable


def test_skills_tabelle_nennt_name_und_anlass():
    skills = [
        SimpleNamespace(name="git-workflow", when_to_use="Wenn du Code committest", description="d1"),
        SimpleNamespace(name="ohne-anlass", when_to_use="", description="Beschreibung als Ersatz"),
    ]
    out = _stable(skills)
    assert "## Skills" in out
    assert "| `git-workflow` | Wenn du Code committest |" in out
    assert "| `ohne-anlass` | Beschreibung als Ersatz |" in out
    assert "`load_skill(name)`" in out


def test_skills_abschnitt_draengt_nicht_zum_vorsorglichen_laden():
    out = _stable([SimpleNamespace(name="a", when_to_use="w", description="d")])
    assert "1%" not in out
    assert "lade ihn zuerst" not in out


def test_ohne_skills_kein_abschnitt():
    assert "## Skills" not in _stable(None)
    assert "## Skills" not in _stable([])
