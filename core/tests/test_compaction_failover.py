"""Compaction-Failover mit ECHTEN Modell-IDs und Kontextfenstern.

Review 09.11.2026: Die erste Fassung testete mit erfundenen Modellnamen (alle 32k-Fenster). Dadurch blieb unsichtbar,
dass ein Fallback mit kleinerem Fenster (Opus 1M → Luna 372k) nie aufgerufen wurde: Die Chunks waren für das
Primärmodell geschnitten, der Guard verwarf sie für den Fallback mit SummaryTooLarge.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.compaction import summarize as summ
from hydrahive.compaction.tokens import context_window_for, estimate_dense_text

PRIMARY = "claude-opus-5-5"
FALLBACK = "openai-codex/gpt-5.6-luna"


def _fake_llm(monkeypatch, calls: list[tuple[str, int]], *, failing: set[str], message: str):
    from hydrahive.runner import llm_bridge

    async def fake(*, model, system_prompt, messages, **kwargs):
        size = estimate_dense_text(system_prompt) + sum(estimate_dense_text(m["content"]) for m in messages)
        calls.append((model, size))
        if model in failing:
            raise RuntimeError(message)
        return [{"type": "text", "text": f"summary via {model}"}], None, None

    monkeypatch.setattr(llm_bridge, "call_with_tools", fake)


def _big_history() -> str:
    """~1 Mio. Zeichen: passt als ein Stück ins Opus-Fenster, aber nicht in Lunas 372k."""
    return "\n".join(f"[User]: frage {i} " + "x" * 400 for i in range(2600))


def test_fenster_sind_wirklich_verschieden():
    assert context_window_for(PRIMARY) > context_window_for(FALLBACK)


def test_fallback_mit_kleinerem_fenster_wird_neu_zerlegt(monkeypatch):
    calls: list[tuple[str, int]] = []
    _fake_llm(monkeypatch, calls, failing={PRIMARY}, message="Error code: 429 rate_limit_error")

    result = asyncio.run(summ.summarize(model=PRIMARY, fallback_models=[FALLBACK], serialized_history=_big_history()))

    assert result == f"summary via {FALLBACK}"
    fallback_calls = [size for model, size in calls if model == FALLBACK]
    assert fallback_calls, "Fallback wurde nie aufgerufen"
    assert max(fallback_calls) <= context_window_for(FALLBACK)


def test_kein_doppeltes_bezahlen_wenn_primaermodell_klappt(monkeypatch):
    calls: list[tuple[str, int]] = []
    _fake_llm(monkeypatch, calls, failing=set(), message="")

    asyncio.run(summ.summarize(model=PRIMARY, fallback_models=[FALLBACK], serialized_history=_big_history()))

    assert {model for model, _ in calls} == {PRIMARY}


def test_connection_fehler_wechselt_in_compaction(monkeypatch):
    calls: list[tuple[str, int]] = []
    _fake_llm(monkeypatch, calls, failing={PRIMARY}, message="APIConnectionError: Cannot connect to host")

    result = asyncio.run(summ.summarize(model=PRIMARY, fallback_models=[FALLBACK], serialized_history="[User]: hallo"))

    assert result == f"summary via {FALLBACK}"


def test_nicht_retrybarer_fehler_wechselt_nicht(monkeypatch):
    calls: list[tuple[str, int]] = []
    _fake_llm(monkeypatch, calls, failing={PRIMARY}, message="invalid response schema")

    with pytest.raises(RuntimeError, match="invalid response schema"):
        asyncio.run(summ.summarize(model=PRIMARY, fallback_models=[FALLBACK], serialized_history="[User]: hallo"))

    assert [model for model, _ in calls] == [PRIMARY]


def test_modellkette_ohne_duplikate(monkeypatch):
    calls: list[tuple[str, int]] = []
    _fake_llm(monkeypatch, calls, failing={PRIMARY}, message="429 rate_limit_exceeded")

    asyncio.run(summ.summarize(model=PRIMARY, fallback_models=[PRIMARY, FALLBACK, FALLBACK],
                               serialized_history="[User]: hallo"))

    assert [model for model, _ in calls] == [PRIMARY, FALLBACK]
