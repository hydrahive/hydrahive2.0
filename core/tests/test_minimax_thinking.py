"""Tests: Interleaved Thinking für MiniMax-Modelle."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from hydrahive.llm._anthropic import EFFORT_TO_BUDGET


def _make_fake_client(captured_kwargs: dict) -> MagicMock:
    async def fake_create(**kwargs):
        captured_kwargs.update(kwargs)
        resp = MagicMock()
        resp.content = []
        resp.stop_reason = "end_turn"
        resp.usage = MagicMock(
            input_tokens=10, output_tokens=5,
            cache_creation_input_tokens=0, cache_read_input_tokens=0,
        )
        return resp

    mock_client = MagicMock()
    mock_client.messages.create = fake_create
    return mock_client


def test_minimax_anthropic_call_setzt_thinking_bei_medium():
    """minimax_anthropic_call übergibt thinking-Block wenn reasoning_effort='medium'."""
    from hydrahive.runner._llm_bridge_backends import minimax_anthropic_call

    captured_kwargs: dict = {}
    mock_client = _make_fake_client(captured_kwargs)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        asyncio.run(minimax_anthropic_call(
            api_key="test-key",
            model="MiniMax-M2.7",
            system_prompt="Test",
            messages=[{"role": "user", "content": "Hallo"}],
            tools=[],
            temperature=0.7,
            max_tokens=4096,
            reasoning_effort="medium",
        ))

    assert "thinking" in captured_kwargs
    assert captured_kwargs["thinking"]["type"] == "enabled"
    assert captured_kwargs["thinking"]["budget_tokens"] == EFFORT_TO_BUDGET["medium"]
    assert captured_kwargs["temperature"] == 1.0


def test_minimax_anthropic_call_kein_thinking_wenn_effort_none():
    """minimax_anthropic_call ohne reasoning_effort → kein thinking-Block."""
    from hydrahive.runner._llm_bridge_backends import minimax_anthropic_call

    captured_kwargs: dict = {}
    mock_client = _make_fake_client(captured_kwargs)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        asyncio.run(minimax_anthropic_call(
            api_key="test-key",
            model="MiniMax-M2.7",
            system_prompt="Test",
            messages=[{"role": "user", "content": "Hallo"}],
            tools=[],
            temperature=0.7,
            max_tokens=4096,
            reasoning_effort=None,
        ))

    assert "thinking" not in captured_kwargs
    assert captured_kwargs["temperature"] == 0.7


def test_m21_ist_minimax_modell():
    from hydrahive.llm._anthropic import is_minimax_model
    assert is_minimax_model("MiniMax-M2.1") is True


def test_m21_in_static_models():
    from hydrahive.llm._catalog_data import STATIC_MODELS
    assert "MiniMax-M2.1" in STATIC_MODELS["minimax"]


def test_m21_metadata_vorhanden():
    from hydrahive.llm._catalog_data import METADATA
    assert "MiniMax-M2.1" in METADATA
    assert METADATA["MiniMax-M2.1"]["tool_use"] is True
    assert METADATA["MiniMax-M2.1"]["context_window"] == 205_000
