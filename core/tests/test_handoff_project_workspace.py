"""Ein an einen Projekt-Spezialisten delegierter Handoff muss im PROJEKT-Workspace
laufen (nicht im leeren Agent-Workspace) — sonst sieht der Spezialist den Code nicht.

Das setzt voraus, dass die Handoff-Session die project_id des Ziel-Agenten erbt;
resolve_run_context weist das Projekt-Workspace nur bei gesetzter session.project_id zu.
"""
from __future__ import annotations

import asyncio

from hydrahive.agentlink.protocol import Handoff, State, TaskBlock, WSEvent
from hydrahive.runner import handoff_receiver as hr


def test_handoff_session_inherits_target_project_id(monkeypatch):
    async def _get_state(_sid):
        return State(
            agent_id="caller",
            task=TaskBlock(type="feature", description="analyse", status="in_progress"),
            handoff=Handoff(to_agent="hydrahive", reason="hh-target:spec-1|hh-task: x"),
        )

    captured: dict = {}

    class _Sess:
        id = "sess-1"

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(hr, "get_state", _get_state)
    monkeypatch.setattr(hr, "_find_target_agent",
                        lambda tid: {"id": "spec-1", "type": "specialist", "project_id": "P",
                                     "owner": "u", "require_tool_confirm": True})
    monkeypatch.setattr(hr.sessions_db, "create", lambda **k: (captured.update(k), _Sess())[1])
    monkeypatch.setattr(hr.db_agent_handoffs, "create", lambda **k: {"id": "h1"})
    monkeypatch.setattr(hr, "_run_and_reply", _noop)

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="s1")))

    assert captured.get("project_id") == "P"
    # Session erbt den ECHTEN Owner des Ziel-Agenten (config-key 'owner'),
    # nicht "admin" — sonst versteckt der owner-gefilterte Aktivitäts-Feed
    # den delegierten Spezialisten vor seinem User.
    assert captured.get("user_id") == "u"
