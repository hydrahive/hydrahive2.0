from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_update_config_probes_and_persists_dynamic_embed_dimension(monkeypatch):
    from hydrahive.api.routes import llm
    from hydrahive.db import mirror
    from hydrahive.llm import embed

    saved = {}
    monkeypatch.setattr(llm, "_load", lambda: {
        "providers": [{"id": "ollama", "name": "Ollama", "api_key": "", "api_base": "http://ollama:11434", "models": []}],
        "embed_model": "",
        "embed_dimensions": {"old/model": 123},
    })
    monkeypatch.setattr(llm, "_save", lambda data: saved.update(data))

    async def models(modality):
        assert modality == "embed"
        return [SimpleNamespace(id="ollama/nomic-embed-text:latest")]

    async def dimension(model):
        assert model == "ollama/nomic-embed-text:latest"
        return 768

    async def changed(model):
        assert model == "ollama/nomic-embed-text:latest"

    monkeypatch.setattr(llm.registry, "list_models", models)
    monkeypatch.setattr(llm.registry, "invalidate", lambda: None)
    monkeypatch.setattr(embed, "ensure_model_dimension", dimension)
    monkeypatch.setattr(mirror, "on_embed_model_change", changed)

    cfg = llm.LlmConfig(
        providers=[{"id": "ollama", "name": "Ollama", "api_key": "", "api_base": "http://ollama:11434", "models": []}],
        embed_model="ollama/nomic-embed-text:latest",
        embed_dimensions={"attacker/model": 65_535},
    )
    result = await llm.update_config(cfg)

    assert result["embed_dimensions"] == {
        "old/model": 123,
        "ollama/nomic-embed-text:latest": 768,
    }
    assert saved == result


@pytest.mark.asyncio
async def test_update_config_rejects_embed_model_missing_from_live_catalog(monkeypatch):
    from fastapi import HTTPException
    from hydrahive.api.routes import llm

    monkeypatch.setattr(llm, "_load", lambda: {"providers": [], "embed_model": ""})

    async def no_models(modality):
        return []

    monkeypatch.setattr(llm.registry, "list_models", no_models)
    with pytest.raises(HTTPException) as exc:
        await llm.update_config(llm.LlmConfig(embed_model="ollama/not-installed"))
    assert exc.value.status_code == 400
