"""Sprach-Block im echten Runner (docs/specs/agent-language.md, Akzeptanz 1–5).

Der LLM-Aufruf ist durch eine Aufzeichnung ersetzt; alles andere (Agent-Config, Memory, Sitzung, Prompt-Bau) ist echt.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult

MODEL = "claude-3-7-sonnet-20250219"
DE = "Antworte immer auf Deutsch"
EN = "Always respond in English"


@pytest.fixture
def world(client, monkeypatch):
    from hydrahive.tools import _memory_store as memory

    seen: list[dict] = []

    async def fake_stream(**kwargs):
        seen.append({"stable": kwargs["stable_system"], "volatile": kwargs["volatile_system"],
                     "summary": kwargs.get("summary_system")})
        yield IterationResult(blocks=[{"type": "text", "text": "ok"}], stop_reason="end_turn",
                              used_model=kwargs["primary_model"], input_tokens=1, output_tokens=1,
                              cache_creation_tokens=0, cache_read_tokens=0)

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    init_db()
    made: list[str] = []

    def agent(owner: str, *, is_buddy: bool = False, language: str | None = None) -> str:
        a = agent_config.create(agent_type="master", name=f"a-{owner}-{len(made)}", llm_model=MODEL, owner=owner,
                                created_by=owner, temperature=0.7, max_tokens=1000, thinking_budget=0)
        if is_buddy:
            agent_config.update(a["id"], is_buddy=True)
        if language is not None:
            memory.write_key(a["id"], "_pref_language", language)
        made.append(a["id"])
        return a["id"]

    def run(agent_id: str, user: str) -> dict:
        s = sessions_db.create(agent_id=agent_id, user_id=user, title="lang")
        before = len(seen)
        asyncio.run(_drain(s.id))
        assert len(seen) > before, "LLM-Aufruf wurde nicht erreicht"
        return seen[-1]

    yield agent, run
    for aid in made:
        agent_config.delete(aid)


async def _drain(session_id: str) -> None:
    async for _ in runner_mod.run(session_id, "hallo"):
        pass


def test_project_agent_gets_buddy_language_in_stable_part(world):
    agent, run = world
    agent("rl-anna", is_buddy=True, language="de")
    worker = agent("rl-anna")
    call = run(worker, "rl-anna")
    assert DE in call["stable"]
    assert DE not in call["volatile"]


def test_english_and_auto(world):
    agent, run = world
    agent("rl-bob", is_buddy=True, language="en")
    call = run(agent("rl-bob"), "rl-bob")
    assert EN in call["stable"] and DE not in call["stable"]
    agent("rl-cleo", is_buddy=True, language="auto")
    call = run(agent("rl-cleo"), "rl-cleo")
    assert DE not in call["stable"] and EN not in call["stable"]


def test_user_without_buddy_gets_german(world):
    agent, run = world
    assert DE in run(agent("rl-dora"), "rl-dora")["stable"]


def test_language_follows_the_run_user_not_the_agent_owner(world):
    """Ein Spezialist (Besitzer = Ziel-Agent-Besitzer, siehe _handoff_setup) läuft für seinen Besitzer. Hier: gleicher
    Agent, zwei Nutzer – entscheidend ist der Nutzer der Sitzung."""
    agent, run = world
    agent("rl-emil", is_buddy=True, language="en")
    agent("rl-fritz", is_buddy=True, language="de")
    shared = agent("rl-emil")
    assert EN in run(shared, "rl-emil")["stable"]
    assert DE in run(shared, "rl-fritz")["stable"]


def test_buddy_itself_gets_the_block(world):
    agent, run = world
    b = agent("rl-gina", is_buddy=True, language="de")
    assert DE in run(b, "rl-gina")["stable"]


def test_stable_part_is_byte_identical_across_runs(world):
    agent, run = world
    agent("rl-hans", is_buddy=True, language="de")
    w = agent("rl-hans")
    assert run(w, "rl-hans")["stable"] == run(w, "rl-hans")["stable"]


def test_block_survives_a_summary(world, monkeypatch):
    """Nach einer Kompaktierung (Zusammenfassung vorhanden) steht der Block weiter im stabilen Teil – er hängt nicht an
    der Zusammenfassung (Ursache vom 03.10.)."""
    from hydrahive.db import messages as messages_db
    agent, run = world
    agent("rl-ida", is_buddy=True, language="de")
    w = agent("rl-ida")
    monkeypatch.setattr(messages_db, "get_latest_summary", lambda sid: "Zusammenfassung ohne jede Sprachregel")
    call = run(w, "rl-ida")
    assert call["summary"] and DE not in call["summary"]
    assert DE in call["stable"]
