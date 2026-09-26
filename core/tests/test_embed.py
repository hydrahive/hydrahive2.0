"""Embedding-Metadaten und dynamisches Provider-Routing."""
from __future__ import annotations

import asyncio

from hydrahive.llm import embed

BGE_M3 = "baai/bge-m3-20251117"


def test_bge_m3_dimension_ist_1024():
    assert embed.dim_for_model(BGE_M3) == 1024
    assert embed.dim_for_model(f"openrouter/{BGE_M3}") == 1024


def test_bge_m3_key_lookup_geht_auf_openrouter():
    """api_base-Pfad löst den Key über den Provider auf — muss 'openrouter' sein."""
    assert embed._PROVIDER_BY_MODEL[BGE_M3] == "openrouter"


def test_bge_m3_nutzt_openrouter_api_base():
    entry = embed._BY_MODEL[BGE_M3]
    assert entry["api_base"] == "https://openrouter.ai/api/v1"


def test_canonical_model_ids_resolve_to_provider_api_names():
    assert embed._provider_and_api_model("ollama/nomic-embed-text:latest") == (
        "ollama", "nomic-embed-text:latest",
    )
    assert embed._provider_and_api_model("nvidia_nim/nvidia/embed-qa-4") == (
        "nvidia", "nvidia/embed-qa-4",
    )
    assert embed._provider_and_api_model("openrouter/baai/bge-m3") == (
        "openrouter", "baai/bge-m3",
    )


def test_ollama_embedding_uses_configured_base_without_api_key(monkeypatch):
    captured = {}

    class Item:
        index = 0
        embedding = [0.1, 0.2, 0.3]

    class Response:
        data = [Item()]

    class Embeddings:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return Response()

    class Client:
        def __init__(self, **kwargs):
            captured.update({"client_" + k: v for k, v in kwargs.items()})
            self.embeddings = Embeddings()

    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {
        "providers": [{"id": "ollama", "api_base": "http://localhost:11434", "api_key": ""}],
    })
    monkeypatch.setattr("openai.AsyncOpenAI", Client)

    result = asyncio.run(embed.aembed_batch(["hello"], "ollama/nomic-embed-text:latest"))

    assert result == [[0.1, 0.2, 0.3]]
    assert captured["client_api_key"] == "ollama"
    assert captured["client_base_url"] == "http://localhost:11434/v1"
    assert captured["model"] == "nomic-embed-text:latest"
