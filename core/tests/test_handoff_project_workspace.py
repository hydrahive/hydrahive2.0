"""Ein an einen Projekt-Spezialisten delegierter Handoff muss im PROJEKT-Workspace
laufen (nicht im leeren Agent-Workspace) — sonst sieht der Spezialist den Code nicht.

Das setzt voraus, dass die Handoff-Session die project_id des Ziel-Agenten erbt;
resolve_run_context weist das Projekt-Workspace nur bei gesetzter session.project_id zu.
"""
from __future__ import annotations

import asyncio

from hydrahive.agentlink.protocol import Handoff, State, TaskBlock, WSEvent
from hydrahive.runner import _handoff_setup as hs
from hydrahive.runner import handoff_receiver as hr


def test_handoff_session_inherits_target_project_id(monkeypatch):
    async def _get_state(_sid):
        return State(
            agent_id="caller",
            task=TaskBlock(type="feature", description="analyse", status="in_progress"),
            handoff=Handoff(
                to_agent="hydrahive",
                reason="hh-target:spec-1|hh-runtime:v1:deep|hh-task: x",
            ),
        )

    captured: dict = {}

    class _Sess:
        id = "sess-1"

    async def _noop(*args, **kwargs):
        captured["run_timeout"] = kwargs.get("run_timeout")

    monkeypatch.setattr(hr, "get_state", _get_state)
    monkeypatch.setattr(hr, "_find_target_agent",
                        lambda tid: {"id": "spec-1", "type": "specialist", "project_id": "P",
                                     "owner": "u", "require_tool_confirm": True,
                                     "handoff_timeout_seconds": 1_200})
    monkeypatch.setattr(hs.sessions_db, "create", lambda **k: (captured.update(k), _Sess())[1])
    monkeypatch.setattr(hr.db_agent_handoffs, "create", lambda **k: {"id": "h1"})
    monkeypatch.setattr(hr, "_run_and_reply", _noop)

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="s1")))

    assert captured.get("project_id") == "P"
    # Session erbt den ECHTEN Owner des Ziel-Agenten (config-key 'owner'),
    # nicht "admin" — sonst versteckt der owner-gefilterte Aktivitäts-Feed
    # den delegierten Spezialisten vor seinem User.
    assert captured.get("user_id") == "u"
    assert captured.get("run_timeout") == 1_200
    assert captured["metadata"]["agentlink_runtime"] == {
        "version": 1,
        "profile": "deep",
        "max_iterations": 16,
        "max_tokens": 16_384,
        "timeout_seconds": 1_200,
    }


def test_resume_reuses_caller_bound_specialist_session(monkeypatch):
    async def _get_state(_sid):
        return State(
            agent_id="hydrahive/project-a",
            task=TaskBlock(type="feature", description="continue", status="in_progress"),
            handoff=Handoff(
                to_agent="hydrahive",
                reason=(
                    "hh-target:spec-1|hh-runtime:v1:quick|"
                    "hh-resume:v1:handoff_old123|hh-task: continue"
                ),
            ),
        )

    class _Sess:
        id = "sess-existing"
        agent_id = "spec-1"
        metadata = {"source": "agentlink", "old": True}

    captured: dict = {}

    async def _noop(*args, **kwargs):
        captured["run_session_id"] = args[1]
        captured["resumed"] = kwargs.get("resumed")

    def _claim(token, **kwargs):
        captured["claim"] = {"token": token, **kwargs}
        return {"session_id": "sess-existing"}

    monkeypatch.setattr(hr, "get_state", _get_state)
    monkeypatch.setattr(
        hr, "_find_target_agent",
        lambda _tid: {
            "id": "spec-1", "type": "specialist", "project_id": "P", "owner": "u",
            "require_tool_confirm": True, "max_iterations": 64, "max_tokens": 24_000,
            "handoff_timeout_seconds": 1_200,
        },
    )
    monkeypatch.setattr(
        hr.db_agent_handoffs, "get_resumable",
        lambda *args, **kwargs: {"session_id": "sess-existing"},
    )
    monkeypatch.setattr(hr.db_agent_handoffs, "claim_resumable", _claim)
    monkeypatch.setattr(hs.sessions_db, "get", lambda _sid: _Sess())
    monkeypatch.setattr(
        hs.sessions_db, "update",
        lambda sid, **changes: captured.update({"updated_session": sid, **changes}),
    )
    monkeypatch.setattr(
        hs.sessions_db, "create", lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Resume darf keine neue Session erzeugen")
        ),
    )
    monkeypatch.setattr(hr.db_agent_handoffs, "create", lambda **_kwargs: {"id": "h-new"})
    monkeypatch.setattr(hr, "_run_and_reply", _noop)

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="state-new")))

    assert captured["claim"] == {
        "token": "handoff_old123",
        "from_agent": "hydrahive/project-a",
        "agent_id": "spec-1",
    }
    assert captured["updated_session"] == "sess-existing"
    assert captured["status"] == "active"
    assert captured["metadata"]["old"] is True
    assert captured["metadata"]["agentlink_runtime"]["profile"] == "quick"
    assert captured["run_session_id"] == "sess-existing"
    assert captured["resumed"] is True


def test_resume_claim_is_restored_when_setup_fails(monkeypatch):
    async def _get_state(_sid):
        return State(
            agent_id="hydrahive/project-a",
            task=TaskBlock(type="feature", description="continue", status="in_progress"),
            handoff=Handoff(
                to_agent="hydrahive",
                reason=(
                    "hh-target:spec-1|hh-runtime:v1:quick|"
                    "hh-resume:v1:handoff_old123|hh-task: continue"
                ),
            ),
        )

    class _Sess:
        id = "sess-existing"
        agent_id = "spec-1"
        metadata = {"source": "agentlink"}

    captured: dict = {}

    async def _error(_state, message):
        captured["error"] = message

    monkeypatch.setattr(hr, "get_state", _get_state)
    monkeypatch.setattr(
        hr, "_find_target_agent",
        lambda _tid: {"id": "spec-1", "status": "active", "require_tool_confirm": True},
    )
    monkeypatch.setattr(
        hr.db_agent_handoffs, "get_resumable",
        lambda *args, **kwargs: {"session_id": "sess-existing"},
    )
    monkeypatch.setattr(
        hr.db_agent_handoffs, "claim_resumable",
        lambda *args, **kwargs: {"session_id": "sess-existing"},
    )
    monkeypatch.setattr(
        hr.db_agent_handoffs, "restore_paused_claim",
        lambda token: captured.setdefault("restored", token) is not None,
    )
    monkeypatch.setattr(hs.sessions_db, "get", lambda _sid: _Sess())
    monkeypatch.setattr(
        hs.sessions_db, "update",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("disk full")),
    )
    monkeypatch.setattr(hr, "_post_error_reply", _error)

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="state-fail")))

    assert captured["restored"] == "handoff_old123"
    assert captured["error"] == "Handoff konnte nicht sicher gestartet werden"


def test_replayed_or_foreign_resume_token_is_rejected(monkeypatch):
    async def _get_state(_sid):
        return State(
            agent_id="hydrahive/project-b",
            task=TaskBlock(type="feature", description="continue", status="in_progress"),
            handoff=Handoff(
                to_agent="hydrahive",
                reason=(
                    "hh-target:spec-1|hh-runtime:v1:standard|"
                    "hh-resume:v1:handoff_old123|hh-task: continue"
                ),
            ),
        )

    captured: dict = {}

    async def _error(_state, message):
        captured["error"] = message

    monkeypatch.setattr(hr, "get_state", _get_state)
    monkeypatch.setattr(
        hr, "_find_target_agent",
        lambda _tid: {"id": "spec-1", "status": "active", "require_tool_confirm": True},
    )
    monkeypatch.setattr(hr.db_agent_handoffs, "get_resumable", lambda *args, **kwargs: None)
    monkeypatch.setattr(hr, "_post_error_reply", _error)
    monkeypatch.setattr(
        hs.sessions_db, "create", lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Abgelehnter Resume darf keine Session erzeugen")
        ),
    )

    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id="state-replay")))

    assert "bereits verwendet" in captured["error"]
