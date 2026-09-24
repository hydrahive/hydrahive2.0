from __future__ import annotations

import asyncio

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult
from hydrahive.tools.base import ToolResult

_AGENT_ID = "test-agent-001"


async def _drain(session_id: str, user_input: str) -> list:
    return [event async for event in runner_mod.run(session_id, user_input)]


def _result(blocks: list[dict], stop_reason: str = "end_turn") -> IterationResult:
    return IterationResult(
        blocks=blocks, stop_reason=stop_reason,
        used_model="claude-3-7-sonnet-20250219",
        input_tokens=1, output_tokens=1,
        cache_creation_tokens=0, cache_read_tokens=0,
    )


def test_runner_persists_completion_claim_observation(setup_test_env, monkeypatch):
    init_db()
    agent_config.update(_AGENT_ID, max_iterations=1, compact_threshold_pct=100)
    session = sessions_db.create(agent_id=_AGENT_ID, user_id="admin", title="integrity-claim")

    async def fake_stream(**kwargs):
        yield _result([{"type": "text", "text": "Der Fix ist erfolgreich getestet."}])

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    asyncio.run(_drain(session.id, "Bitte prüfe den Fix"))

    assistant = [m for m in messages_db.list_for_session(session.id) if m.role == "assistant"][0]
    integrity = assistant.metadata["integrity"]
    assert integrity["mode"] == "observe"
    assert integrity["snapshot"]["completion_claims"] == 1
    assert integrity["signals"][0]["kind"] == "completion_claim"


def test_runner_continues_recent_evidence_for_direct_resume(setup_test_env, monkeypatch):
    init_db()
    agent_config.update(_AGENT_ID, max_iterations=1, compact_threshold_pct=100)
    session = sessions_db.create(agent_id=_AGENT_ID, user_id="admin", title="integrity-resume")
    messages_db.append(
        session.id, "assistant", "previous",
        metadata={"integrity": {
            "mode": "observe",
            "snapshot": {"evidence_kinds": ["artifact_changed", "tests_passed"]},
            "signals": [],
        }},
    )

    async def fake_stream(**kwargs):
        yield _result([{"type": "text", "text": "Der Fix ist weiterhin getestet."}])

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    asyncio.run(_drain(session.id, "weiter"))

    assistant = [
        message for message in messages_db.list_for_session(session.id)
        if message.role == "assistant"
    ][-1]
    integrity = assistant.metadata["integrity"]
    kinds = {signal["kind"] for signal in integrity["signals"]}
    assert "evidence_continued" in kinds
    assert "unverified_completion_claim" not in kinds
    assert integrity["snapshot"]["continued_evidence"] == 2


def test_runner_passes_state_to_tools_and_persists_snapshot(setup_test_env, monkeypatch):
    init_db()
    agent_config.update(
        _AGENT_ID, max_iterations=1, compact_threshold_pct=100, tools=["shell_exec"],
    )
    session = sessions_db.create(agent_id=_AGENT_ID, user_id="admin", title="integrity-tool")

    async def fake_stream(**kwargs):
        yield _result([{
            "type": "tool_use", "id": "toolu_integrity", "name": "shell_exec",
            "input": {"cmd": "echo hi"},
        }], stop_reason="tool_use")

    async def fake_process(tool_uses, **kwargs):
        state = kwargs["integrity_state"]
        state.record_tool("shell_exec", {"cmd": "echo hi"}, ToolResult.ok("hi"))
        yield [{"type": "tool_result", "tool_use_id": "toolu_integrity", "content": "hi"}]

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)
    asyncio.run(_drain(session.id, "Führe den Check aus"))

    tool_message = [
        m for m in messages_db.list_for_session(session.id)
        if m.role == "user" and isinstance(m.content, list)
    ][0]
    integrity = tool_message.metadata["integrity"]
    assert integrity["mode"] == "observe"
    assert integrity["snapshot"]["tool_observations"] == 1
    assert integrity["snapshot"]["new_evidence"] == 1
