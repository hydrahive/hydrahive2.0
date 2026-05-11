"""Tests für llm_calls — DB-Wrapper, Pricing-Lookup, Provider-Heuristik (Token-Audit #129)."""
from __future__ import annotations

from hydrahive.db import init_db
from hydrahive.db import llm_calls as llm_calls_db
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._pricing import (
    cost_micros,
    lookup,
    provider_from_model,
)


def _make_session() -> str:
    init_db()
    s = sessions_db.create(agent_id="test-agent-001", user_id="testuser", title="llm_calls-test")
    return s.id


def test_insert_und_for_session_roundtrip(setup_test_env):
    session_id = _make_session()
    call = llm_calls_db.LlmCall(
        session_id=session_id,
        agent_id="test-agent-001",
        user_id="testuser",
        provider="anthropic",
        model="claude-sonnet-4-7-20250101",
        temperature=0.7,
        max_tokens=4096,
        reasoning_effort=None,
        prompt_tokens=1000,
        completion_tokens=200,
        cache_read_tokens=500,
        cache_creation_tokens=100,
        stop_reason="end_turn",
        ttft_ms=None,
        total_ms=1234,
        cost_micros=cost_micros(
            "anthropic", "claude-sonnet-4-7-20250101",
            prompt_tokens=1000, completion_tokens=200,
            cache_read_tokens=500, cache_creation_tokens=100,
        ),
        turn_in_session=1,
    )
    call_id = llm_calls_db.insert(call)
    assert call_id.startswith("llmc_")

    rows = llm_calls_db.for_session(session_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == call_id
    assert row["session_id"] == session_id
    assert row["provider"] == "anthropic"
    assert row["model"] == "claude-sonnet-4-7-20250101"
    assert row["prompt_tokens"] == 1000
    assert row["completion_tokens"] == 200
    assert row["cache_read_tokens"] == 500
    assert row["cache_creation_tokens"] == 100
    assert row["turn_in_session"] == 1
    assert row["total_ms"] == 1234
    assert row["cost_micros"] is not None and row["cost_micros"] > 0


def test_provider_from_model_heuristik():
    assert provider_from_model("claude-sonnet-4-7-20250101") == "anthropic"
    assert provider_from_model("claude-3-5-haiku-20241022") == "anthropic"
    assert provider_from_model("gpt-4o-2024-11-20") == "openai"
    assert provider_from_model("gpt-5") == "openai"
    assert provider_from_model("o1-preview") == "openai"
    assert provider_from_model("o3-mini") == "openai"
    assert provider_from_model("deepseek-chat") == "deepseek"
    assert provider_from_model("gemini-2.0-flash") == "gemini"
    assert provider_from_model("qwen2.5-72b") == "qwen"
    assert provider_from_model("llama-3.3-70b") == "ollama"
    assert provider_from_model("mistral-large") == "ollama"
    assert provider_from_model("minimax-abab") == "minimax"
    assert provider_from_model("völlig-unbekannt") == "other"


def test_pricing_lookup_prefix_match():
    # Sonnet 4.7 mit Datum-Suffix → matcht 'claude-sonnet-4'
    p = lookup("anthropic", "claude-sonnet-4-7-20251015")
    assert p is not None
    assert p.input == 0.3
    assert p.output == 1.5
    assert p.cache_read == 0.03
    assert p.cache_creation == 0.375

    # Opus 4.x
    p = lookup("anthropic", "claude-opus-4-7")
    assert p is not None
    assert p.input == 1.5
    assert p.output == 7.5

    # 3.5 Haiku — spezifischerer Prefix gewinnt vor generischem 'claude'
    p = lookup("anthropic", "claude-3-5-haiku-20241022")
    assert p is not None
    assert p.input == 0.08


def test_pricing_lookup_unknown_returns_none():
    assert lookup("anthropic", "claude-irgendwas-neu-99") is None
    assert lookup("unknown-provider", "irgendwas") is None


def test_cost_micros_anthropic_sonnet():
    # Sonnet 4.x: $3 input, $15 output → 0.3 micros/token input, 1.5 micros/token output
    # cache_read $0.30 → 0.03 micros/token; cache_creation $3.75 → 0.375 micros/token
    cost = cost_micros(
        "anthropic", "claude-sonnet-4-7-20250101",
        prompt_tokens=1000, completion_tokens=200,
        cache_read_tokens=500, cache_creation_tokens=100,
    )
    # 1000*0.3 + 200*1.5 + 500*0.03 + 100*0.375 = 300 + 300 + 15 + 37.5 = 652.5 → 652 (round)
    assert cost == 652 or cost == 653  # Rundungstoleranz


def test_cost_micros_unknown_returns_none():
    cost = cost_micros(
        "ollama", "llama-3.3-70b",
        prompt_tokens=1000, completion_tokens=200,
        cache_read_tokens=0, cache_creation_tokens=0,
    )
    assert cost is None
