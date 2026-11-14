"""Harte Bindung an Templates (Plan E3 T3+T4, Spec agent-templates.md Kap. 5).

- Gebundener Agent: Modell, Fallback und Budget sind am Agenten nicht änderbar (nur über das Template).
- `template` wechseln geht; unbekanntes Template wird abgelehnt.
- Ungebundener Agent: alles wie bisher.
- Anlegen mit `template`: Pflichtwerte (llm_model …) kommen aus dem Template.
"""
from __future__ import annotations

import pytest

from hydrahive.agents import AgentValidationError
from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents._binding import BOUND_FIELDS, default_template_for
from hydrahive.agents.templates import _store

KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}
OLD = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch, client):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    yield
    _store.reset_cache()


@pytest.fixture
def agent():
    made: list[str] = []

    def make(template: str | None = None, agent_type: str = "specialist") -> dict:
        a = agent_config.create(agent_type=agent_type, name=f"bound-{len(made)}", llm_model=OLD, owner="b-anna",
                                created_by="b-anna", temperature=0.7, max_tokens=1000, thinking_budget=0,
                                template=template)
        made.append(a["id"])
        return a
    yield make
    for aid in made:
        agent_config.delete(aid)


@pytest.mark.parametrize("field", sorted(BOUND_FIELDS))
def test_gebunden_feld_nicht_aenderbar(agent, field):
    a = agent("reviewer")
    value = {"llm_model": "claude-sonnet-5", "fallback_models": ["claude-sonnet-5"], "cache_ttl": "5m",
             "reasoning_effort": "low", "compact_model": "claude-sonnet-5"}.get(field, 7 if "pct" not in field else 50)
    with pytest.raises(AgentValidationError, match="agent_bound_to_template"):
        agent_config.update(a["id"], **{field: value})


def test_unveraendert_mitgeschickt_ist_erlaubt(agent):
    """Die Einstellungsseite schickt das ganze Objekt; gleiche Werte zählen nicht als Änderung."""
    a = agent("reviewer")
    agent_config.update(a["id"], llm_model=a["llm_model"], max_tokens=a["max_tokens"], description="neu")
    assert agent_config.get(a["id"])["description"] == "neu"


def test_template_wechseln(agent):
    a = agent("reviewer")
    agent_config.update(a["id"], template="backend")
    assert agent_config.get(a["id"])["template"] == "backend"


def test_unbekanntes_template_abgelehnt(agent):
    a = agent("reviewer")
    with pytest.raises(AgentValidationError, match="template_unknown"):
        agent_config.update(a["id"], template="gibts-nicht")


def test_ungebunden_wie_bisher(agent):
    a = agent(None)
    agent_config.update(a["id"], max_iterations=77)
    assert agent_config.get(a["id"])["max_iterations"] == 77


def test_anlegen_mit_template_setzt_modell_aus_template(agent):
    a = agent("projekt-master", agent_type="project")
    assert a["template"] == "projekt-master" and a["llm_model"] == "claude-opus-5-5"


def test_anlegen_unbekanntes_template(agent):
    with pytest.raises(AgentValidationError, match="template_unknown"):
        agent("gibts-nicht")


@pytest.mark.parametrize(("agent_type", "name", "expected"), [
    ("master", "till's Buddy", "buddy"),
    ("master", "till's Assistant", "assistant"),
    ("project", "x — Projekt-Agent", "projekt-master"),
    ("specialist", "Hilfe-Assistent", "hilfe"),
    ("specialist", "irgendwas", "recherche"),
])
def test_standard_template_je_typ(agent_type, name, expected):
    assert default_template_for(agent_type, name) == expected
