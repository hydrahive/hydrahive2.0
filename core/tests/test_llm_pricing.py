"""#145 OpenRouter Pricing-Tracking.

provider_from_model() muss openrouter/-Präfix erkennen.
cost_micros() darf für OpenRouter keine Exception werfen (Option A: None).
"""
from __future__ import annotations

from hydrahive.llm._pricing import cost_micros, provider_from_model


def test_openrouter_prefix_erkannt():
    assert provider_from_model("openrouter/mistralai/mistral-large") == "openrouter"


def test_openrouter_prefix_erkannt_kurz():
    assert provider_from_model("openrouter/x-ai/grok-4.20") == "openrouter"


def test_andere_provider_unveraendert():
    assert provider_from_model("claude-sonnet-4-6") == "anthropic"
    assert provider_from_model("gpt-4o") == "openai"
    assert provider_from_model("unknown-model-xyz") == "other"


def test_cost_micros_openrouter_gibt_none_nicht_crash():
    result = cost_micros(
        "openrouter", "openrouter/mistralai/mistral-large",
        prompt_tokens=1000, completion_tokens=500,
        cache_read_tokens=0, cache_creation_tokens=0,
    )
    assert result is None
