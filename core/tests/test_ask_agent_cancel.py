"""Agent bricht eigene Hintergrund-Aufträge ab (Hindernis 4, 01.10.2026).

Vorher ging das nur über den Knopf im Chat. Ein Agent, der merkt, dass ein
Auftrag falsch war (z. B. tote Aufträge nach einem Fehler), konnte nur bis
zum Fristende warten. Jetzt: ask_agent(cancel="<Auftrags-ID>").
Sicherheit: nur Aufträge DERSELBEN Session; Kurz-ID (8 Zeichen) wie in der
Rückmeldung von ask_agent erlaubt.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from hydrahive.db import delegations as delegations_db
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.tools import ToolContext, ask_agent


@pytest.fixture
def setup(setup_test_env):
    init_db()
    mine = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="mein").id
    other = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="fremd").id
    mk = lambda sid, sfx: delegations_db.create(
        session_id=sid, agent_id="test-agent-001", user_id="admin", target_agent_id="t",
        target_name="Prüfer", task="x", state_id=f"st-cancel-{sfx}-{uuid.uuid4().hex[:8]}", depth=1, timeout_seconds=600)
    return mine, other, mk(mine, "a"), mk(other, "b")


def _ctx(sid, tmp_path):
    return ToolContext(session_id=sid, agent_id="test-agent-001", user_id="admin",
                       workspace=tmp_path, origin="chat")


def _run(args, ctx):
    return asyncio.run(ask_agent.TOOL.execute(args, ctx))


def test_eigener_auftrag_per_kurz_id(setup, tmp_path):
    mine, _other, d_mine, _d_other = setup
    res = _run({"cancel": d_mine["id"][-8:]}, _ctx(mine, tmp_path))
    assert res.success, res.error
    assert delegations_db.get(d_mine["id"])["status"] == "cancelled"


def test_fremde_session_wird_nicht_abgebrochen(setup, tmp_path):
    mine, _other, _d_mine, d_other = setup
    res = _run({"cancel": d_other["id"]}, _ctx(mine, tmp_path))
    assert not res.success
    assert delegations_db.get(d_other["id"])["status"] == "running"


def test_schon_fertig_meldet_das_ehrlich(setup, tmp_path):
    mine, _o, d_mine, _d = setup
    delegations_db.complete_if_running(d_mine["id"], "done", "fertig")
    res = _run({"cancel": d_mine["id"]}, _ctx(mine, tmp_path))
    assert not res.success and "läuft nicht mehr" in res.error


def test_cancel_braucht_kein_agent_id_und_task(setup, tmp_path):
    """Schema: agent_id/task sind nur fürs Beauftragen Pflicht."""
    assert "cancel" in ask_agent.TOOL.schema["properties"]
    assert "agent_id" not in ask_agent.TOOL.schema.get("required", [])
    assert "task" not in ask_agent.TOOL.schema.get("required", [])


def test_ohne_cancel_bleibt_beauftragen_unveraendert(setup, tmp_path):
    mine, *_ = setup
    res = _run({"task": "x"}, _ctx(mine, tmp_path))
    assert not res.success and "agent_id fehlt" in res.error
