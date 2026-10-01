"""Stopp mitten in einer Werkzeug-Runde verliert keine fertigen Ergebnisse.

Belegt 30.09.2026 (Session 01a0e01b): Drei ask_agent-Aufrufe in EINER Runde.
Der erste war um 22:51 fertig (Ergebnis in tool_calls), der Nutzer stoppte um
22:57 während des zweiten. Weil runner.py die tool_result-Blöcke erst nach
ALLEN Werkzeugen speicherte, fehlte das fertige Ergebnis im Verlauf. Beim
nächsten Turn setzte heal_orphan_tool_uses „Truncation im vorigen Turn“ ein,
und tool_calls blieb auf 'pending'.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult
from hydrahive.runner.context import heal_orphan_tool_uses

AGENT_ID = "test-agent-001"

TOOLS = [
    {"type": "tool_use", "id": "toolu_a", "name": "shell_exec", "input": {"cmd": "echo a"}},
    {"type": "tool_use", "id": "toolu_b", "name": "shell_exec", "input": {"cmd": "sleep 99"}},
]


def _session() -> str:
    init_db()
    return sessions_db.create(agent_id=AGENT_ID, user_id="admin", title="cancel-test").id


def _patch(monkeypatch, started: asyncio.Event) -> None:
    async def fake_stream(**kwargs):
        yield IterationResult(
            blocks=TOOLS, stop_reason="tool_use", used_model=kwargs["primary_model"],
            input_tokens=1, output_tokens=1, cache_creation_tokens=0, cache_read_tokens=0,
        )

    async def fake_process(tool_uses, *, ctx, parent_message_id, sink=None, **kw):
        # Werkzeug A ist fertig (tool_calls-Zeile 'success'), B hängt (pending).
        rec_a = tools_db.create(parent_message_id, "shell_exec", {"cmd": "echo a"},
                                session_id=ctx.session_id, tool_use_id="toolu_a")
        tools_db.finish(rec_a.id, result={"output": "a"}, status="success")
        block_a = {"type": "tool_result", "tool_use_id": "toolu_a", "content": "a", "is_error": False}
        if sink is not None:
            sink.append(block_a)
        tools_db.create(parent_message_id, "shell_exec", {"cmd": "sleep 99"},
                        session_id=ctx.session_id, tool_use_id="toolu_b")
        started.set()
        await asyncio.sleep(30)
        yield [block_a]

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)
    monkeypatch.setattr(runner_mod, "should_compact", lambda *a, **k: False)


def _run_and_cancel(sid: str, started: asyncio.Event) -> None:
    async def scenario():
        async def drain():
            async for _ in runner_mod.run(sid, "mach zwei Sachen"):
                pass
        task = asyncio.create_task(drain())
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


def _tool_result_blocks(sid: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for m in messages_db.list_for_session(sid):
        if m.role == "user" and isinstance(m.content, list):
            for b in m.content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    out[b["tool_use_id"]] = b
    return out


def test_finished_result_is_kept_when_run_is_stopped(monkeypatch, setup_test_env):
    sid = _session()
    started = asyncio.Event()
    _patch(monkeypatch, started)
    _run_and_cancel(sid, started)

    blocks = _tool_result_blocks(sid)
    assert blocks["toolu_a"]["content"] == "a"
    assert blocks["toolu_a"]["is_error"] is False
    assert blocks["toolu_b"]["is_error"] is True
    assert "gestoppt" in blocks["toolu_b"]["content"]
    assert "Truncation" not in blocks["toolu_b"]["content"]


def test_pending_tool_calls_are_marked_cancelled(monkeypatch, setup_test_env):
    sid = _session()
    started = asyncio.Event()
    _patch(monkeypatch, started)
    _run_and_cancel(sid, started)

    statuses = {tc.tool_use_id: tc.status for tc in tools_db.list_for_session(sid)}
    assert statuses == {"toolu_a": "success", "toolu_b": "cancelled"}


def test_heal_text_no_longer_claims_truncation():
    from hydrahive.db.messages import Message
    hist = [Message(id="m1", session_id="s", role="assistant",
                    content=[TOOLS[0]], created_at="t", token_count=None, metadata={})]
    healed = heal_orphan_tool_uses(hist)
    text = healed[-1].content[0]["content"]
    assert "Truncation" not in text
    assert "unterbrochen" in text
