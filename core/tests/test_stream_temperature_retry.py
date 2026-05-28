"""Test H3: anthropic_stream retry'd ohne temperature wenn das Modell sie ablehnt.

Der Bug: das try/except umschloss nur den synchronen Stream-Manager; der echte
Request feuert in __aenter__ (async with) — außerhalb des try. Ein
BadRequestError (temperature deprecated bei opus 4.7/4.8) propagierte ungefangen,
der Retry passierte nie und die Session endete als 'abandoned'.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest


def _bad_request_temperature():
    import anthropic
    resp = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    return anthropic.BadRequestError(
        "temperature is deprecated for this model", response=resp, body=None
    )


class _FakeFinal:
    stop_reason = "end_turn"
    content: list = []
    usage = None


class _FakeStreamObj:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration

    async def get_final_message(self):
        return _FakeFinal()


class _FakeManager:
    def __init__(self, should_raise: bool):
        self._should_raise = should_raise

    async def __aenter__(self):
        if self._should_raise:
            raise _bad_request_temperature()
        return _FakeStreamObj()

    async def __aexit__(self, *exc):
        return False


def _run_collect(agen):
    async def _drain():
        return [ev async for ev in agen]
    return asyncio.run(_drain())


def test_stream_retried_ohne_temperature(monkeypatch):
    """Erster Versuch (mit temperature) wirft deprecated → Retry ohne temperature läuft durch."""
    calls: list[dict] = []

    class FakeMessages:
        def stream(self, **kwargs):
            calls.append(kwargs)
            # Erster Aufruf hat temperature → wirft beim __aenter__; Retry hat keine mehr.
            return _FakeManager(should_raise="temperature" in kwargs)

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.runner._stream_providers import anthropic_stream
    events = _run_collect(anthropic_stream(
        key="sk-test", model="claude-opus-4-8", system_prompt="s",
        messages=[{"role": "user", "content": "hi"}], tools=[],
        temperature=1.0, max_tokens=1024,
    ))

    # Zwei stream()-Aufrufe: erster mit temperature (wirft), zweiter ohne (Retry).
    assert len(calls) == 2
    assert "temperature" in calls[0]
    assert "temperature" not in calls[1]
    # Der Retry liefert ein sauberes message_stop — Session bricht NICHT ab.
    assert any(e["type"] == "message_stop" for e in events)


def test_stream_ohne_fehler_kein_retry(monkeypatch):
    """Wenn das Modell temperature akzeptiert: genau ein stream()-Aufruf, kein Retry."""
    calls: list[dict] = []

    class FakeMessages:
        def stream(self, **kwargs):
            calls.append(kwargs)
            return _FakeManager(should_raise=False)

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.runner._stream_providers import anthropic_stream
    events = _run_collect(anthropic_stream(
        key="sk-test", model="claude-sonnet-4-6", system_prompt="s",
        messages=[{"role": "user", "content": "hi"}], tools=[],
        temperature=0.7, max_tokens=1024,
    ))

    assert len(calls) == 1
    assert any(e["type"] == "message_stop" for e in events)


def test_stream_anderer_bad_request_wird_durchgereicht(monkeypatch):
    """Ein BadRequestError ohne 'temperature/deprecated' wird NICHT geschluckt."""
    def _other_bad_request():
        import anthropic
        resp = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
        return anthropic.BadRequestError("invalid model xyz", response=resp, body=None)

    class _RaisingManager:
        async def __aenter__(self):
            raise _other_bad_request()

        async def __aexit__(self, *exc):
            return False

    class FakeMessages:
        def stream(self, **kwargs):
            return _RaisingManager()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.runner._stream_providers import anthropic_stream

    with pytest.raises(anthropic.BadRequestError):
        _run_collect(anthropic_stream(
            key="sk-test", model="claude-opus-4-8", system_prompt="s",
            messages=[{"role": "user", "content": "hi"}], tools=[],
            temperature=1.0, max_tokens=1024,
        ))
