"""Baustein „Arbeitsweise“ im System-Prompt je Rolle (Plan E6 T3, Spec agent-templates.md Kap. 9)."""
from __future__ import annotations

from pathlib import Path

from hydrahive.runner import system_prompt
from hydrahive.runner._working_style import working_style


def test_rolle_aus_dem_agent():
    assert "Buddy" in working_style({"is_buddy": True, "type": "master"})
    assert "Projekt-Agent" in working_style({"type": "project"})
    assert "Spezialist" in working_style({"type": "specialist"})
    assert working_style({"type": "master"}) == ""            # andere Master-Agenten: kein fester Ablauf


def test_projekt_agent_delegiert_mit_briefing():
    text = working_style({"type": "project"})
    assert "ask_agent" in text and "goal" in text and "deliverable" in text


def test_spezialist_antwortformat():
    text = working_style({"type": "specialist"})
    assert "## Ergebnis" in text


def test_ordnung_im_workspace_fuer_alle_drei_rollen():
    for agent in ({"is_buddy": True, "type": "master"}, {"type": "project"}, {"type": "specialist"}):
        text = working_style(agent)
        assert "## Ordnung im Workspace" in text
        assert "|| exit 1" in text
        assert "_work/" in text
        assert "bereich-" in text


def test_ordnung_im_workspace_nicht_fuer_andere_master():
    assert working_style({"type": "master"}) == ""


def test_ordnung_im_workspace_ist_stabil_ohne_datum():
    import re
    text = working_style({"type": "specialist"})
    abschnitt = text.split("## Ordnung im Workspace", 1)[1]
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", abschnitt)


def _compose(agent):
    return system_prompt.compose("BASIS", extra_system=None, workspace=Path("/tmp/w"), summary=None, skills=None,
                                 longterm_memory=False, tool_schemas=[], allowed_tools=[], agent=agent)


def test_im_stabilen_teil_nicht_im_volatilen():
    stable, volatile, _ = _compose({"type": "project"})
    assert "## Arbeitsweise" in stable and "## Arbeitsweise" not in volatile


def test_ohne_agent_unveraendert():
    stable, _, _ = _compose(None)
    assert "## Arbeitsweise" not in stable
