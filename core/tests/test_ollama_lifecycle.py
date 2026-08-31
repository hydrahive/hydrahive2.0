from __future__ import annotations

import asyncio

import pytest

from hydrahive.llm import ollama_lifecycle


@pytest.fixture(autouse=True)
def _reset_jobs():
    ollama_lifecycle._reset_jobs()
    yield
    ollama_lifecycle._reset_jobs()


def test_progress_parser_tracks_digest_and_total_without_leaking_upstream_error():
    job = ollama_lifecycle.PullJob(id="j1", model="qwen3:14b")
    ollama_lifecycle._apply_progress(job, '{"status":"pulling manifest"}')
    ollama_lifecycle._apply_progress(job, '{"status":"downloading","digest":"sha256:abc","total":100,"completed":25}')
    assert job.status == "pulling"
    assert job.phase == "downloading"
    assert job.total == 100
    assert job.completed == 25

    with pytest.raises(ollama_lifecycle.PullFailed, match="ollama_pull_failed"):
        ollama_lifecycle._apply_progress(job, '{"error":"secret upstream detail"}')


def test_start_pull_is_idempotent_while_same_model_is_active(monkeypatch):
    release = asyncio.Event()

    async def fake_run(provider, job):
        job.status = "pulling"
        await release.wait()
        job.status = "success"

    monkeypatch.setattr(ollama_lifecycle, "_run_pull", fake_run)

    async def scenario():
        provider = {"api_base": "http://localhost:11434"}
        first = await ollama_lifecycle.start_pull(provider, "qwen3:14b")
        second = await ollama_lifecycle.start_pull(provider, "ollama/qwen3:14b")
        assert first["id"] == second["id"]
        release.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert ollama_lifecycle.get_pull(first["id"])["status"] == "success"

    asyncio.run(scenario())


def test_model_references_cover_defaults_provider_and_agents(monkeypatch):
    monkeypatch.setattr(ollama_lifecycle, "load_config", lambda: {
        "default_model": "ollama/qwen3:14b",
        "embed_model": "ollama/nomic-embed-text",
        "providers": [{"id": "ollama", "models": ["ollama/qwen3:14b"]}],
    })
    monkeypatch.setattr(ollama_lifecycle.agent_config, "list_all", lambda: [
        {"name": "Coder", "llm_model": "ollama/qwen3:14b", "fallback_models": ["ollama/llama3.2"]},
    ])
    refs = ollama_lifecycle.model_references("qwen3:14b")
    assert refs == ["Standardmodell", "Ollama-Providerliste", "Agent: Coder"]


def test_delete_refuses_referenced_model_before_upstream_call(monkeypatch):
    monkeypatch.setattr(ollama_lifecycle, "model_references", lambda model: ["Agent: Coder"])
    called = False

    async def fake_delete(provider, model):
        nonlocal called
        called = True

    monkeypatch.setattr(ollama_lifecycle.ollama_client, "delete_model", fake_delete)

    async def scenario():
        with pytest.raises(ollama_lifecycle.ModelInUse) as exc:
            await ollama_lifecycle.delete_model({"api_base": "http://localhost:11434"}, "qwen3:14b")
        assert exc.value.references == ["Agent: Coder"]

    asyncio.run(scenario())
    assert called is False
