"""Tests für Pre-Resume-Compaction bei max_iterations (#143).

Verifiziert dass der Runner — wenn er in max_iterations läuft und die History
groß ist — vor dem `session_end(paused)` einmal compactes.  Damit der "Weiter-
machen"-Button nicht direkt wieder nach 16 Iter knallt.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult
from hydrahive.runner.events import Error
from hydrahive.tools._sessions import session_get


AGENT_ID = "test-agent-001"


def _setup_agent_for_max_iter() -> None:
    """max_iterations=1 damit jeder Run sofort in den paused-Pfad fällt."""
    agent_config.update(AGENT_ID, max_iterations=1, compact_threshold_pct=75)


def _new_session() -> str:
    init_db()
    s = sessions_db.create(agent_id=AGENT_ID, user_id="admin", title="max-iter-test")
    return s.id


def _patch_stream_with_tool_use(monkeypatch) -> None:
    """Mockt stream_llm_call so dass jede Iteration einen tool_use yieldet.
    Damit läuft der Runner in den Tool-Loop und ohne max_iter=1 nicht raus.
    """
    async def fake_stream(**kwargs):
        yield IterationResult(
            blocks=[{"type": "tool_use", "id": "toolu_test1",
                     "name": "shell_exec", "input": {"command": "echo hi"}}],
            stop_reason="tool_use", used_model=kwargs["primary_model"],
            input_tokens=100, output_tokens=20,
            cache_creation_tokens=0, cache_read_tokens=0,
        )

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)


def _patch_process_tool_uses_passthrough(monkeypatch) -> None:
    """Mockt process_tool_uses → liefert sofort leere result_blocks."""
    async def fake_process(tool_uses, **kwargs):
        yield [{"type": "tool_result", "tool_use_id": tu["id"], "content": "ok"}
               for tu in tool_uses]

    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)


async def _drain(session_id: str) -> list:
    return [e async for e in runner_mod.run(session_id, "test prompt")]


def test_pre_resume_compactes_bei_grosser_history(setup_test_env, monkeypatch):
    """should_compact==True → compact_session mit triggered_by='max_iterations_resume'."""
    _setup_agent_for_max_iter()
    sid = _new_session()
    _patch_stream_with_tool_use(monkeypatch)
    _patch_process_tool_uses_passthrough(monkeypatch)

    monkeypatch.setattr(runner_mod, "should_compact", lambda *a, **kw: True)
    fake_compact = AsyncMock(return_value={})
    monkeypatch.setattr(runner_mod, "compact_session", fake_compact)

    events = asyncio.run(_drain(sid))

    assert any(isinstance(e, Error) and e.metadata.get("kind") == "max_iterations"
               for e in events), "Erwartet: max_iterations-Error wird trotzdem geyielded"
    assert fake_compact.call_count == 1
    kwargs = fake_compact.call_args.kwargs
    assert kwargs["triggered_by"] == "max_iterations_resume"
    assert kwargs["trigger_threshold_pct"] == 50
    assert session_get(AGENT_ID, sid)["status"] == "paused"


def test_pre_resume_skip_bei_kleiner_history(setup_test_env, monkeypatch):
    """should_compact==False → kein compact_session-Call, trotzdem paused."""
    _setup_agent_for_max_iter()
    sid = _new_session()
    _patch_stream_with_tool_use(monkeypatch)
    _patch_process_tool_uses_passthrough(monkeypatch)

    monkeypatch.setattr(runner_mod, "should_compact", lambda *a, **kw: False)
    fake_compact = AsyncMock(return_value={})
    monkeypatch.setattr(runner_mod, "compact_session", fake_compact)

    events = asyncio.run(_drain(sid))

    assert any(isinstance(e, Error) for e in events)
    assert fake_compact.call_count == 0
    assert session_get(AGENT_ID, sid)["status"] == "paused"


def test_pre_resume_skip_wenn_compaction_global_aus(setup_test_env, monkeypatch):
    """compact_threshold_pct=100 → kein Compaction-Call (auch bei großer History)."""
    agent_config.update(AGENT_ID, max_iterations=1, compact_threshold_pct=100)
    sid = _new_session()
    _patch_stream_with_tool_use(monkeypatch)
    _patch_process_tool_uses_passthrough(monkeypatch)

    # should_compact würde True liefern, darf aber gar nicht aufgerufen werden
    fake_should = lambda *a, **kw: pytest.fail("should_compact darf bei threshold=100 nicht laufen")
    monkeypatch.setattr(runner_mod, "should_compact", fake_should)
    fake_compact = AsyncMock(return_value={})
    monkeypatch.setattr(runner_mod, "compact_session", fake_compact)

    events = asyncio.run(_drain(sid))

    assert any(isinstance(e, Error) for e in events)
    assert fake_compact.call_count == 0
    assert session_get(AGENT_ID, sid)["status"] == "paused"


def test_pre_resume_compaction_exception_swallowed(setup_test_env, monkeypatch):
    """Wenn compact_session crasht: Error trotzdem geyielded, Session=paused."""
    _setup_agent_for_max_iter()
    sid = _new_session()
    _patch_stream_with_tool_use(monkeypatch)
    _patch_process_tool_uses_passthrough(monkeypatch)

    monkeypatch.setattr(runner_mod, "should_compact", lambda *a, **kw: True)

    async def boom(*a, **kw):
        raise RuntimeError("compaction kaputt")

    monkeypatch.setattr(runner_mod, "compact_session", boom)

    events = asyncio.run(_drain(sid))

    assert any(isinstance(e, Error) and e.metadata.get("kind") == "max_iterations"
               for e in events), "Error muss trotz Compaction-Crash kommen"
    assert session_get(AGENT_ID, sid)["status"] == "paused"
