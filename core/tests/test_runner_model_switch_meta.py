"""Runner speichert Modellwechsel in den Metadaten der Antwort (Plan E1 T6).

Der LLM-Aufruf ist ersetzt; Agent-Config, Sitzung und Nachrichten-DB sind echt.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult

MODEL = "claude-3-7-sonnet-20250219"
SWITCH = {"from_model": MODEL, "to_model": "openai-codex/gpt-5.6-terra", "reason": "rate_limit"}


@pytest.fixture
def world(client, monkeypatch):
    switches: list[list[dict]] = [[]]

    async def fake_stream(**kwargs):
        yield IterationResult(blocks=[{"type": "text", "text": "ok"}], stop_reason="end_turn",
                              used_model="openai-codex/gpt-5.6-terra", input_tokens=1, output_tokens=1,
                              cache_creation_tokens=0, cache_read_tokens=0, switches=switches[0])

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    init_db()
    a = agent_config.create(agent_type="master", name="switch-meta", llm_model=MODEL, owner="sm-anna",
                            created_by="sm-anna", temperature=0.7, max_tokens=1000, thinking_budget=0)

    def run(sw: list[dict]) -> dict:
        switches[0] = sw
        s = sessions_db.create(agent_id=a["id"], user_id="sm-anna", title="switch")

        async def drain():
            async for _ in runner_mod.run(s.id, "hallo"):
                pass
        asyncio.run(drain())
        msgs = [m for m in messages_db.list_for_session(s.id) if m.role == "assistant"]
        return msgs[-1].metadata or {}

    yield run
    agent_config.delete(a["id"])


def test_wechsel_steht_in_den_metadaten(world):
    meta = world([SWITCH])
    assert meta["model_switches"] == [SWITCH]
    assert meta["model"] == "openai-codex/gpt-5.6-terra"


def test_ohne_wechsel_kein_feld(world):
    assert "model_switches" not in world([])
