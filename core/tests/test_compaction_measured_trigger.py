"""Regression 09.11.2026: Compaction zündete nicht, obwohl der Provider 998k von 1M Tokens meldete.

Die Zeichen-Schätzung sah nur 685k (Schwelle 700k). Der zweite Trigger nutzt die gemessene Prompt-Größe.
"""
from __future__ import annotations

from hydrahive.db._message_model import Message
from hydrahive.runner import _runner_iter as ri
from hydrahive.runner._measured_usage import measured_history_tokens, prompt_tokens_from_metadata

OPUS = "claude-opus-5-5"  # Fenster 1M, 70 % → Schwelle 700k


def _msg(role: str, created_at: str, content: str = "x", **meta) -> Message:
    return Message(id=created_at, session_id="s", role=role, content=content, created_at=created_at, metadata=meta)


def _assistant(created_at: str, *, model: str = OPUS, inp: int = 2, read: int = 0, create: int = 0) -> Message:
    return _msg("assistant", created_at, model=model, input_tokens=inp,
                cache_read_tokens=read, cache_creation_tokens=create)


def test_anthropic_counts_cache_separately():
    meta = {"model": OPUS, "input_tokens": 2, "cache_read_tokens": 997_485, "cache_creation_tokens": 1_061}
    assert prompt_tokens_from_metadata(meta) == 998_548


def test_codex_input_already_contains_cache():
    meta = {"model": "openai-codex/gpt-5.6-sol", "input_tokens": 300_000, "cache_read_tokens": 290_000}
    assert prompt_tokens_from_metadata(meta) == 300_000


def test_missing_or_broken_metadata_is_zero():
    assert prompt_tokens_from_metadata(None) == 0
    assert prompt_tokens_from_metadata({"input_tokens": "kaputt"}) == 0


def test_measured_adds_messages_since_last_call():
    history = [_msg("user", "01"), _assistant("02", read=500_000), _msg("user", "03", content="y" * 3500)]
    total = measured_history_tokens(history, model=OPUS, compacted_at=None)
    assert total >= 500_000 + 1000


def test_other_model_measurement_is_ignored():
    history = [_assistant("01", model="openai-codex/gpt-5.6-sol", inp=900_000)]
    assert measured_history_tokens(history, model=OPUS, compacted_at=None) == 0


def test_measurement_before_compaction_is_ignored():
    """Behaltene Nachrichten von vor der Compaction dürfen keine Compaction-Schleife auslösen."""
    history = [_assistant("01", read=990_000), _msg("user", "03")]
    assert measured_history_tokens(history, model=OPUS, compacted_at="02") == 0


def test_no_assistant_message_is_zero():
    assert measured_history_tokens([_msg("user", "01")], model=OPUS, compacted_at=None) == 0


async def _run_prepare(monkeypatch, history, *, compacted_at=None):
    calls: list[str] = []

    async def fake_compact(session_id, **kwargs):
        calls.append(kwargs["model"])

    monkeypatch.setattr(ri.messages_db, "list_for_llm", lambda sid: history)
    monkeypatch.setattr(ri.messages_db, "latest_compaction_at", lambda sid: compacted_at)
    monkeypatch.setattr(ri, "_auto_compaction_cooldown_active", lambda sid: False)
    monkeypatch.setattr(ri, "compact_session", fake_compact)
    async for _ in ri.prepare_history(
        "s", model=OPUS, compact_model=OPUS, compact_fallback_models=[], compact_tool_limit=None,
        compact_reserve=16_384, compact_threshold_pct=70, compact_max_turns=None,
    ):
        pass
    return calls


async def test_prepare_history_compacts_on_measured_size(monkeypatch):
    # Schätzung winzig, Provider meldet 998k → muss compacten (das war der Bug).
    history = [_msg("user", "01"), _assistant("02", read=997_485, create=1_061), _msg("user", "03")]
    assert await _run_prepare(monkeypatch, history) == [OPUS]


async def test_prepare_history_skips_below_threshold(monkeypatch):
    history = [_msg("user", "01"), _assistant("02", read=400_000), _msg("user", "03")]
    assert await _run_prepare(monkeypatch, history) == []


async def test_prepare_history_no_loop_after_compaction(monkeypatch):
    history = [_assistant("01", read=990_000), _msg("user", "03")]
    assert await _run_prepare(monkeypatch, history, compacted_at="02") == []
