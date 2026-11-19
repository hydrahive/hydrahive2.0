"""Regressionstest für den Timeout-Bug bei verschachtelten ask_agent-Ketten
(Befund 2026-11-19): handoff_receiver.handle() MUSS den eigenen Lauf mit
origin=handoff(depth) starten, sonst darf der empfangende Agent selbst keine
Spezialisten mehr im Hintergrund beauftragen (ask_agent läuft dann synchron
und die Timeouts der Kette summieren sich, bis der äusserste Aufrufer
abläuft, während innere Spezialisten noch arbeiten).
"""
from __future__ import annotations

import asyncio

from hydrahive.agentlink import signing
from hydrahive.agentlink.protocol import Handoff, State, TaskBlock, WSEvent
from hydrahive.agentlink.runtime_profiles import reason_with_profile
from hydrahive.runner import _handoff_setup as hs
from hydrahive.runner import handoff_receiver as hr
from hydrahive.runner._run_origin import RunOrigin


def _target_agent() -> dict:
    return {
        "id": "spec-1", "type": "specialist", "project_id": "P", "owner": "u",
        "require_tool_confirm": True, "handoff_timeout_seconds": 1_200,
    }


def _wire(monkeypatch, reason: str) -> dict:
    async def _get_state(_sid):
        return signing.sign(State(
            agent_id="caller",
            task=TaskBlock(type="feature", description="analyse", status="in_progress"),
            handoff=Handoff(to_agent="hydrahive", reason=reason),
        ))

    class _Sess:
        id = "sess-1"

    captured: dict = {}

    async def _capture_run_and_reply(*args, **kwargs):
        captured["origin"] = kwargs.get("origin")

    monkeypatch.setattr(hr, "get_state", _get_state)
    monkeypatch.setattr(hr.db_agent_handoffs, "seen", lambda _sid: False)
    monkeypatch.setattr(hr, "_find_target_agent", lambda _tid: _target_agent())
    monkeypatch.setattr(hs.sessions_db, "create", lambda **_k: _Sess())
    monkeypatch.setattr(hr.db_agent_handoffs, "create", lambda **_k: {"id": "h1"})
    monkeypatch.setattr(hr, "_run_and_reply", _capture_run_and_reply)
    return captured


def test_incoming_handoff_without_depth_segment_starts_with_depth_one(monkeypatch):
    """Alter/direkter Reason ohne hh-depth (z.B. Chat → ask_agent): Aufrufer
    gilt als Tiefe 0, unser eigener Lauf bekommt depth=1."""
    reason = reason_with_profile("spec-1", "quick", "analyse")
    captured = _wire(monkeypatch, reason)

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="s1")))

    origin = captured["origin"]
    assert isinstance(origin, RunOrigin)
    assert origin.kind == "handoff"
    assert origin.depth == 1
    # Hintergrund-Delegation muss erlaubt sein, sonst wiederholt sich der Bug.
    assert origin.background_allowed is True
    # Auftragstext kommt vom Auftraggeber-Agenten, nicht vom Endnutzer.
    assert origin.trusted_user_input is False


def test_incoming_handoff_propagates_and_increments_caller_depth(monkeypatch):
    """Ein Aufrufer, der selbst schon in einer Kette steckt (depth=1 aus
    seiner eigenen ctx.origin_depth), gibt das über caller_depth weiter —
    unser Lauf muss depth=2 bekommen."""
    reason = reason_with_profile("spec-1", "quick", "analyse", caller_depth=1)
    captured = _wire(monkeypatch, reason)

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="s1")))

    origin = captured["origin"]
    assert origin.kind == "handoff"
    assert origin.depth == 2
