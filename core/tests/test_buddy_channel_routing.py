"""Eingehende Kanäle (WhatsApp, Discord, Mail, Voice) landen beim Buddy.

Regression: _find_master nahm den ersten Master nach Sortierung der Agenten-IDs.
Wer neben dem Buddy noch den automatisch angelegten „<user>'s Assistant“ hat,
landete je nach ID beim Assistant statt beim Buddy.
"""
from __future__ import annotations

import pytest

USER = "routing-user"


@pytest.fixture(autouse=True)
def _clean(setup_test_env):
    from hydrahive.agents import config as agent_config

    def wipe():
        for a in agent_config.list_by_owner(USER):
            agent_config.delete(a["id"])

    wipe()
    yield
    wipe()


def _master(name: str, *, buddy: bool = False, status: str | None = None) -> dict:
    from hydrahive.agents import config as agent_config

    agent = agent_config.create(
        agent_type="master", name=name, llm_model="claude-sonnet-4-6", owner=USER,
        created_by=USER, temperature=1.0, max_tokens=1000, thinking_budget=0,
    )
    changes = {}
    if buddy:
        changes["is_buddy"] = True
    if status:
        changes["status"] = status
    return agent_config.update(agent["id"], **changes) if changes else agent


def test_buddy_gewinnt_gegen_assistant_unabhaengig_von_der_id_reihenfolge():
    from hydrahive.agents import config as agent_config
    from hydrahive.agents.primary import primary_agent_for

    assistant = _master(f"{USER}'s Assistant")
    buddy = _master(f"{USER}'s Buddy", buddy=True)
    # Beide Reihenfolgen abdecken: die Auswahl darf nicht von der Sortierung abhängen.
    ordered_ids = [a["id"] for a in agent_config.list_by_owner(USER)]
    assert set(ordered_ids) == {assistant["id"], buddy["id"]}
    assert primary_agent_for(USER)["id"] == buddy["id"]


def test_ohne_buddy_bleibt_der_erste_aktive_master():
    from hydrahive.agents.primary import primary_agent_for

    assistant = _master(f"{USER}'s Assistant")
    assert primary_agent_for(USER)["id"] == assistant["id"]


def test_deaktivierter_buddy_faellt_auf_anderen_master_zurueck():
    from hydrahive.agents.primary import primary_agent_for

    assistant = _master(f"{USER}'s Assistant")
    _master(f"{USER}'s Buddy", buddy=True, status="disabled")
    assert primary_agent_for(USER)["id"] == assistant["id"]


def test_kein_master_ergibt_none():
    from hydrahive.agents.primary import primary_agent_for

    assert primary_agent_for(USER) is None


def test_kanal_glue_nimmt_buddy_auch_wenn_assistant_zuerst_sortiert(monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.communication import _agent_glue

    buddy = _master(f"{USER}'s Buddy", buddy=True)
    assistant = _master(f"{USER}'s Assistant")
    # Genau der Fehlerfall: der Assistant steht in der Liste vor dem Buddy.
    real = agent_config.list_by_owner
    monkeypatch.setattr(agent_config, "list_by_owner", lambda owner: sorted(
        real(owner), key=lambda a: a["id"] != assistant["id"]))
    assert agent_config.list_by_owner(USER)[0]["id"] == assistant["id"]
    assert _agent_glue._find_master(USER)["id"] == buddy["id"]
