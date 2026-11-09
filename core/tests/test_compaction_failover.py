"""Compaction nutzt nur konfigurierte Fallbackmodelle und bleibt sequenziell."""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.compaction import summarize as summ


def _fake_llm(monkeypatch, calls: list[str], *, fail_message: str):
    from hydrahive.runner import llm_bridge

    async def fake(*, model, **kwargs):
        calls.append(model)
        if model == "primary-model":
            raise RuntimeError(fail_message)
        return [{"type": "text", "text": f"summary via {model}"}], None, None

    monkeypatch.setattr(llm_bridge, "call_with_tools", fake)


def test_compaction_nutzt_konfiguriertes_fallback_bei_rate_limit(monkeypatch):
    calls: list[str] = []
    _fake_llm(monkeypatch, calls, fail_message="429 rate_limit_exceeded")

    result = asyncio.run(summ.summarize(
        model="primary-model",
        fallback_models=["fallback-model"],
        serialized_history="[User]: hallo",
    ))

    assert result == "summary via fallback-model"
    assert calls == ["primary-model", "fallback-model"]


def test_compaction_nutzt_fallback_bei_connection_error(monkeypatch):
    calls: list[str] = []
    _fake_llm(monkeypatch, calls, fail_message="APIConnectionError: Cannot connect to host")

    result = asyncio.run(summ.summarize(
        model="primary-model",
        fallback_models=["fallback-model"],
        serialized_history="[User]: hallo",
    ))

    assert result == "summary via fallback-model"
    assert calls == ["primary-model", "fallback-model"]


def test_compaction_wechselt_bei_nicht_retrybarem_fehler_nicht(monkeypatch):
    calls: list[str] = []
    _fake_llm(monkeypatch, calls, fail_message="invalid response schema")

    with pytest.raises(RuntimeError, match="invalid response schema"):
        asyncio.run(summ.summarize(
            model="primary-model",
            fallback_models=["fallback-model"],
            serialized_history="[User]: hallo",
        ))

    assert calls == ["primary-model"]


def test_compaction_dedupliziert_modellkette(monkeypatch):
    calls: list[str] = []
    _fake_llm(monkeypatch, calls, fail_message="429 rate_limit_exceeded")

    result = asyncio.run(summ.summarize(
        model="primary-model",
        fallback_models=["primary-model", "fallback-model", "fallback-model"],
        serialized_history="[User]: hallo",
    ))

    assert result == "summary via fallback-model"
    assert calls == ["primary-model", "fallback-model"]
