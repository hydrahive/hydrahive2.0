"""Runner nutzt das Template des Agenten (Plan E2 T5).

LLM-Aufruf ersetzt; Agent-Config, Sitzung, Template-Speicher echt.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._run_settings import chain_with_override, run_settings
from hydrahive.runner._runner_iter import IterationResult

KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}
OLD_MODEL = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    _store.reset_cache()
    yield
    _store.reset_cache()


@pytest.fixture
def world(client, monkeypatch):
    seen: list[dict] = []

    async def fake_stream(**kw):
        seen.append(kw)
        yield IterationResult(blocks=[{"type": "text", "text": "ok"}], stop_reason="end_turn",
                              used_model=kw["primary_model"], input_tokens=1, output_tokens=1,
                              cache_creation_tokens=0, cache_read_tokens=0)

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    init_db()
    made: list[str] = []

    def agent(template: str | None) -> dict:
        a = agent_config.create(agent_type="specialist", name=f"rt-{len(made)}", llm_model=OLD_MODEL, owner="rt-anna",
                                created_by="rt-anna", temperature=0.7, max_tokens=1000, thinking_budget=0,
                                fallback_models=["claude-sonnet-5"])
        if template:
            agent_config.update(a["id"], template=template)
        made.append(a["id"])
        return agent_config.get(a["id"])

    def run(agent_id: str, override: str | None = None) -> dict:
        s = sessions_db.create(agent_id=agent_id, user_id="rt-anna", title="tpl")
        if override:
            sessions_db.update(s.id, metadata={"model_override": override})

        async def drain():
            async for _ in runner_mod.run(s.id, "hallo"):
                pass
        asyncio.run(drain())
        return seen[-1]

    yield agent, run
    for aid in made:
        agent_config.delete(aid)


def test_template_kette_und_budget(world):
    agent, run = world
    a = agent("projekt-master")
    call = run(a["id"])
    assert call["primary_model"] == "claude-opus-5-5"
    assert call["fallback_models"] == ["openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"]
    assert call["max_tokens"] == 32_768 and call["reasoning_effort"] == "high"
    assert call["cooldown_seconds"] == 300


def test_ohne_template_wie_bisher(world):
    agent, run = world
    a = agent(None)
    call = run(a["id"])
    assert call["primary_model"] == OLD_MODEL and call["fallback_models"] == ["claude-sonnet-5"]
    assert call["max_tokens"] == 1000


def test_sitzungsmodell_vor_der_kette(world):
    agent, run = world
    a = agent("projekt-master")
    call = run(a["id"], override="openai-codex/gpt-5.6-terra")
    assert call["primary_model"] == "openai-codex/gpt-5.6-terra"
    assert call["fallback_models"] == ["claude-opus-5-5", "MiniMax-M3.1-Flash"]


def test_iterationen_aus_template():
    tpl.save("klein", {**tpl.get("klein"), "budget": {**tpl.get("klein")["budget"], "max_iterations": 3}}, by="admin")
    rs = run_settings({"template": "klein", "llm_model": OLD_MODEL})
    assert rs.max_iterations == 3 and rs.template_id == "klein"


def test_delegiertes_budget_hat_vorrang():
    class B:
        max_iterations, max_tokens = 7, 999
    rs = run_settings({"template": "reviewer", "llm_model": OLD_MODEL}, session_budget=B())
    assert (rs.max_iterations, rs.max_tokens) == (7, 999)


def test_override_ohne_template_ersetzt_nur_primaer():
    rs = run_settings({"llm_model": "a", "fallback_models": ["b"]})
    assert chain_with_override(rs, "c") == ("c", ["b"])
    assert chain_with_override(rs, None) == ("a", ["b"])
