from __future__ import annotations

import asyncio

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult
from hydrahive.tools.base import ToolContext

_AGENT_ID = "test-agent-001"


@pytest.mark.parametrize(
    "user_input,expected",
    [
        ("Lade genau diesen Film", "Lade genau diesen Film"),
        (
            [
                {"type": "text", "text": "Lade den Film"},
                {"type": "image", "source": {"type": "url", "url": "https://evil"}},
                {"type": "text", "text": "in 1080p"},
            ],
            "Lade den Film in 1080p",
        ),
    ],
)
def test_runner_sets_trusted_current_user_input(
    setup_test_env, monkeypatch, user_input, expected
):
    init_db()
    agent_config.update(
        _AGENT_ID, max_iterations=1, compact_threshold_pct=100,
        tools=["shell_exec"],
    )
    session = sessions_db.create(
        agent_id=_AGENT_ID, user_id="admin", title="trusted-turn-test"
    )
    captured = []

    async def fake_stream(**kwargs):
        yield IterationResult(
            blocks=[{
                "type": "tool_use", "id": "toolu_trusted", "name": "shell_exec",
                "input": {
                    "current_user_input": "vom Modell manipuliert",
                    "current_user_turn_id": "vom Modell manipuliert",
                },
            }],
            stop_reason="tool_use", used_model=kwargs["primary_model"],
            input_tokens=1, output_tokens=1,
            cache_creation_tokens=0, cache_read_tokens=0,
        )

    async def fake_process(tool_uses, **kwargs):
        captured.append(kwargs["ctx"])
        yield []

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)
    asyncio.run(_drain(session.id, user_input))

    assert captured[0].current_user_input == expected
    assert captured[0].current_user_turn_id
    assert captured[0].current_user_turn_id != "vom Modell manipuliert"


async def _drain(session_id: str, user_input):
    return [event async for event in runner_mod.run(session_id, user_input)]


def test_tool_context_field_is_optional_for_backwards_compatibility(tmp_path):
    context = ToolContext(
        session_id="s", agent_id="a", user_id="u", workspace=tmp_path
    )
    assert context.current_user_input is None
    assert context.current_user_turn_id is None
