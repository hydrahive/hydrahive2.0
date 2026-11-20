"""Abbruch stoppt die ganze Kette (runner/delegation_control.cancel).

Befund 20.11.2026 (Auftrag 5257951b): Der Buddy brach den Projekt-Agenten ab; dessen
Frontend-Spezialist (Delegation 01a1fad3) arbeitete noch bis 21:26 weiter.
"""
from __future__ import annotations

import uuid

from hydrahive.db import agent_handoffs as handoffs_db
from hydrahive.db import delegations as delegations_db
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import concurrency, delegation_control

pytest_plugins = ["tests.test_background_delegation"]


def _session(title: str) -> str:
    return sessions_db.create(agent_id="test-agent-001", user_id="admin", title=title).id


def _delegate(parent_sid: str, depth: int, name: str) -> tuple[dict, str]:
    """Auftrag von parent_sid an einen Agenten, inkl. Ziel-Session (wie im echten Ablauf über agent_handoffs)."""
    state_id = f"st-{uuid.uuid4().hex}"
    d = delegations_db.create(session_id=parent_sid, agent_id="a", user_id="admin", target_agent_id=name,
                              target_name=name, task="t", state_id=state_id, depth=depth, timeout_seconds=600)
    child_sid = _session(name)
    handoffs_db.create(incoming_state_id=state_id, from_agent="hydrahive", agent_id=name, session_id=child_sid)
    return d, child_sid


def test_abbruch_oben_stoppt_alle_ebenen(client, monkeypatch):
    init_db()
    buddy = _session("buddy")
    pa_deleg, pa_sid = _delegate(buddy, 1, "projekt-agent")
    fe_deleg, fe_sid = _delegate(pa_sid, 2, "frontend")
    be_deleg, be_sid = _delegate(pa_sid, 2, "backend")
    tief_deleg, tief_sid = _delegate(fe_sid, 3, "helfer")
    stopped: list[str] = []
    monkeypatch.setattr(concurrency, "cancel", lambda sid: stopped.append(sid) or True)
    monkeypatch.setattr(delegation_control, "cancel_pending", lambda _sid: None)

    assert delegation_control.cancel(delegations_db.get(pa_deleg["id"])) is True

    for d in (pa_deleg, fe_deleg, be_deleg, tief_deleg):
        assert delegations_db.get(d["id"])["status"] == "cancelled", d["target_name"]
    assert set(stopped) == {pa_sid, fe_sid, be_sid, tief_sid}
    assert stopped.index(tief_sid) < stopped.index(fe_sid) < stopped.index(pa_sid)   # von unten nach oben


def test_fertige_kinder_bleiben_unberuehrt(client, monkeypatch):
    init_db()
    buddy = _session("buddy")
    pa_deleg, pa_sid = _delegate(buddy, 1, "projekt-agent")
    done_deleg, _ = _delegate(pa_sid, 2, "fertig")
    delegations_db.complete_if_running(done_deleg["id"], "done", "ok")
    monkeypatch.setattr(concurrency, "cancel", lambda sid: True)
    monkeypatch.setattr(delegation_control, "cancel_pending", lambda _sid: None)
    delegation_control.cancel(delegations_db.get(pa_deleg["id"]))
    assert delegations_db.get(done_deleg["id"])["status"] == "done"


def test_zyklus_endet(client, monkeypatch):
    """Kaputte Daten (Kind zeigt auf die eigene Session) dürfen keine Endlosschleife erzeugen."""
    init_db()
    buddy = _session("buddy")
    pa_deleg, pa_sid = _delegate(buddy, 1, "projekt-agent")
    state_id = f"st-{uuid.uuid4().hex}"
    delegations_db.create(session_id=pa_sid, agent_id="a", user_id="admin", target_agent_id="x", target_name="x",
                          task="t", state_id=state_id, depth=2, timeout_seconds=600)
    handoffs_db.create(incoming_state_id=state_id, from_agent="hydrahive", agent_id="x", session_id=pa_sid)
    monkeypatch.setattr(concurrency, "cancel", lambda sid: True)
    monkeypatch.setattr(delegation_control, "cancel_pending", lambda _sid: None)
    assert delegation_control.cancel(delegations_db.get(pa_deleg["id"])) is True


def test_schutz_gegen_endlose_ketten(monkeypatch):
    """_cancel_below besucht jede Session höchstens einmal und geht nicht tiefer als _MAX_CHAIN_DEPTH –
    unabhängig davon, ob der Status-Wechsel die Rekursion zufällig auch stoppen würde."""
    calls: list[str] = []
    child = {"id": "x", "status": "running", "state_id": "s"}
    monkeypatch.setattr(delegation_control.delegations_db, "list_for_session", lambda sid, limit=100: calls.append(sid) or [child])
    monkeypatch.setattr(delegation_control, "cancel", lambda d, depth=0, seen=None: delegation_control._cancel_below("loop", depth, seen) >= 0)
    delegation_control._cancel_below("loop", 0, set())
    assert calls == ["loop"]                                  # Zyklus: dieselbe Session nur einmal
    calls.clear()
    assert delegation_control._cancel_below("tief", delegation_control._MAX_CHAIN_DEPTH, set()) == 0
    assert calls == []                                        # Tiefengrenze greift
