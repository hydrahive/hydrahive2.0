from __future__ import annotations

import hydrahive.llm.model_provider as model_provider


def test_provider_for_model_prefers_configured_provider(monkeypatch):
    monkeypatch.setattr(model_provider, "load_config", lambda: {
        "providers": [
            {"id": "ollama", "models": ["llama3.2"]},
            {"id": "openai", "models": ["custom-gpt"]},
        ]
    })

    assert model_provider.provider_for_model("llama3.2") == "local"
    assert model_provider.provider_for_model("custom-gpt") == "openai"


def test_provider_for_model_uses_backend_conventions(monkeypatch):
    monkeypatch.setattr(model_provider, "load_config", lambda: {"providers": []})

    assert model_provider.provider_for_model("claude-sonnet-4-6") == "anthropic"
    assert model_provider.provider_for_model("openai/gpt-4o") == "openai"
    assert model_provider.provider_for_model("minimax/hailuo-2.3") == "minimax"
    assert model_provider.provider_for_model("ollama/qwen2.5") == "local"
    assert model_provider.provider_for_model("google/gemini-2.5-flash") == "openrouter"
    assert model_provider.provider_for_model("") == "unknown"
