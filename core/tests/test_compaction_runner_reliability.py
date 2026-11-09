"""Auto-Compaction: Cooldown und subagent-sicheres Weiterarbeiten."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from hydrahive.runner import _runner_iter
from hydrahive.runner.events import CompactionStart


async def _collect(**kwargs):
    return [item async for item in _runner_iter.prepare_history("session-1", **kwargs)]


def _kwargs() -> dict:
    return {
        "model": "primary-model",
        "compact_model": "compact-model",
        "compact_fallback_models": ["configured-fallback"],
        "compact_tool_limit": 1_000,
        "compact_reserve": 16_384,
        "compact_threshold_pct": 75,
        "compact_max_turns": None,
    }


def test_auto_cooldown_nach_frischem_fehler(monkeypatch):
    monkeypatch.setattr(
        _runner_iter.compaction_events_db,
        "latest_for_session",
        lambda _session_id: {
            "created_at": "2026-11-09T10:00:00.000+00:00",
            "error": "RateLimitError",
        },
    )
    now = datetime(2026, 11, 9, 10, 4, 59, tzinfo=timezone.utc)
    assert _runner_iter._auto_compaction_cooldown_active("session-1", now=now) is True


def test_auto_cooldown_nach_fuenf_minuten_abgelaufen(monkeypatch):
    monkeypatch.setattr(
        _runner_iter.compaction_events_db,
        "latest_for_session",
        lambda _session_id: {
            "created_at": "2026-11-09T10:00:00.000+00:00",
            "error": "RateLimitError",
        },
    )
    now = datetime(2026, 11, 9, 10, 5, 0, tzinfo=timezone.utc)
    assert _runner_iter._auto_compaction_cooldown_active("session-1", now=now) is False


def test_externe_cancellation_aktiviert_keinen_cooldown(monkeypatch):
    monkeypatch.setattr(
        _runner_iter.compaction_events_db,
        "latest_for_session",
        lambda _session_id: {
            "created_at": "2026-11-09T10:00:00.000+00:00",
            "error": "CancelledError: Compaction extern abgebrochen",
        },
    )
    now = datetime(2026, 11, 9, 10, 1, 0, tzinfo=timezone.utc)
    assert _runner_iter._auto_compaction_cooldown_active("session-1", now=now) is False


def test_erfolgreiches_letztes_event_aktiviert_keinen_cooldown(monkeypatch):
    monkeypatch.setattr(
        _runner_iter.compaction_events_db,
        "latest_for_session",
        lambda _session_id: {
            "created_at": "2026-11-09T10:00:00.000+00:00",
            "error": None,
        },
    )
    now = datetime(2026, 11, 9, 10, 1, 0, tzinfo=timezone.utc)
    assert _runner_iter._auto_compaction_cooldown_active("session-1", now=now) is False


def test_prepare_history_arbeitet_im_cooldown_ohne_compaction_weiter(monkeypatch):
    history = ["original-history"]
    monkeypatch.setattr(_runner_iter.messages_db, "list_for_llm", lambda _session_id: history)
    monkeypatch.setattr(_runner_iter, "should_compact", lambda *args, **kwargs: True)
    monkeypatch.setattr(_runner_iter, "_auto_compaction_cooldown_active", lambda _session_id: True)

    called = False

    async def compact(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(_runner_iter, "compact_session", compact)
    items = asyncio.run(_collect(**_kwargs()))

    assert called is False
    assert items == [history]
    assert not any(isinstance(item, CompactionStart) for item in items)


def test_prepare_history_schluckt_subagent_cancellation_nicht(monkeypatch):
    monkeypatch.setattr(_runner_iter.messages_db, "list_for_llm", lambda _session_id: ["before"])
    monkeypatch.setattr(_runner_iter, "should_compact", lambda *args, **kwargs: True)
    monkeypatch.setattr(_runner_iter, "_auto_compaction_cooldown_active", lambda _session_id: False)

    async def cancelled(*args, **kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(_runner_iter, "compact_session", cancelled)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_collect(**_kwargs()))


def test_prepare_history_reicht_nur_konfigurierte_fallbacks_durch(monkeypatch):
    histories = iter([["before"], ["after"]])
    monkeypatch.setattr(_runner_iter.messages_db, "list_for_llm", lambda _session_id: next(histories))
    monkeypatch.setattr(_runner_iter, "should_compact", lambda *args, **kwargs: True)
    monkeypatch.setattr(_runner_iter, "_auto_compaction_cooldown_active", lambda _session_id: False)
    received: dict = {}

    async def compact(*args, **kwargs):
        received.update(kwargs)

    monkeypatch.setattr(_runner_iter, "compact_session", compact)
    items = asyncio.run(_collect(**_kwargs()))

    assert isinstance(items[0], CompactionStart)
    assert items[-1] == ["after"]
    assert received["fallback_models"] == ["configured-fallback"]
