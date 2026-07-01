"""hydrahive.llm._anthropic: complete/stream retry'n ohne temperature, wenn das
Modell sie ablehnt (BadRequestError 'temperature is deprecated for this model').

Bug: test_stream_temperature_retry.py deckt bereits den Runner-Pfad
(hydrahive.runner._stream_providers) ab — DIESER Pfad (hydrahive.llm._anthropic,
genutzt von llm_client.complete()/stream(), u.a. vom Modell-Test-Button
/api/llm/catalog/test) hatte den Retry NICHT. Neuere Claude-Modelle (opus-4-7+,
sonnet-5) crashten dort mit einem rohen 400 statt zu funktionieren.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest


def _bad_request_temperature():
    import anthropic
    resp = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    return anthropic.BadRequestError(
        "temperature is deprecated for this model", response=resp, body=None
    )


def _other_bad_request():
    import anthropic
    resp = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    return anthropic.BadRequestError("invalid model xyz", response=resp, body=None)


class _FakeRawResp:
    def __init__(self, content: list, headers=None):
        self.headers = headers or {}
        self._content = content

    def parse(self):
        from types import SimpleNamespace
        return SimpleNamespace(content=self._content)


class _FakeTextBlock:
    type = "text"
    text = "OK"


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- anthropic_complete
def test_anthropic_complete_retried_ohne_temperature(monkeypatch):
    calls: list[dict] = []

    class FakeRawResponseNS:
        async def create(self, **kwargs):
            calls.append(kwargs)
            if "temperature" in kwargs:
                raise _bad_request_temperature()
            return _FakeRawResp([_FakeTextBlock()])

    class FakeMessages:
        with_raw_response = FakeRawResponseNS()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)
    monkeypatch.setattr(
        "hydrahive.llm._oauth_usage.extract_rate_limit_headers", lambda headers: None
    )

    from hydrahive.llm._anthropic import anthropic_complete
    out = _run(anthropic_complete(
        key="sk-ant-test", messages=[{"role": "user", "content": "hi"}],
        model="claude-opus-4-8", temperature=1.0, max_tokens=1024,
    ))

    assert len(calls) == 2
    assert "temperature" in calls[0]
    assert "temperature" not in calls[1]
    assert out == "OK"


def test_anthropic_complete_ohne_fehler_kein_retry(monkeypatch):
    calls: list[dict] = []

    class FakeRawResponseNS:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return _FakeRawResp([_FakeTextBlock()])

    class FakeMessages:
        with_raw_response = FakeRawResponseNS()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)
    monkeypatch.setattr(
        "hydrahive.llm._oauth_usage.extract_rate_limit_headers", lambda headers: None
    )

    from hydrahive.llm._anthropic import anthropic_complete
    out = _run(anthropic_complete(
        key="sk-ant-test", messages=[{"role": "user", "content": "hi"}],
        model="claude-sonnet-4-6", temperature=0.7, max_tokens=1024,
    ))

    assert len(calls) == 1
    assert out == "OK"


def test_anthropic_complete_anderer_bad_request_durchgereicht(monkeypatch):
    class FakeRawResponseNS:
        async def create(self, **kwargs):
            raise _other_bad_request()

    class FakeMessages:
        with_raw_response = FakeRawResponseNS()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.llm._anthropic import anthropic_complete
    with pytest.raises(anthropic.BadRequestError):
        _run(anthropic_complete(
            key="sk-ant-test", messages=[{"role": "user", "content": "hi"}],
            model="claude-opus-4-8", temperature=1.0, max_tokens=1024,
        ))


# ---------------------------------------------------------------- minimax_complete
def test_minimax_complete_retried_ohne_temperature(monkeypatch):
    calls: list[dict] = []

    class FakeMessages:
        async def create(self, **kwargs):
            calls.append(kwargs)
            if "temperature" in kwargs:
                raise _bad_request_temperature()
            from types import SimpleNamespace
            return SimpleNamespace(content=[_FakeTextBlock()])

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.llm._anthropic import minimax_complete
    out = _run(minimax_complete(
        api_key="key", messages=[{"role": "user", "content": "hi"}],
        model="MiniMax-M2", temperature=1.0, max_tokens=1024,
    ))

    assert len(calls) == 2 and "temperature" not in calls[1]
    assert out == "OK"


# ---------------------------------------------------------------- anthropic_stream / minimax_stream
class _FakeStreamObj:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration

    @property
    def text_stream(self):
        return self


class _FakeManager:
    def __init__(self, should_raise: bool):
        self._should_raise = should_raise

    async def __aenter__(self):
        if self._should_raise:
            raise _bad_request_temperature()
        return _FakeStreamObj()

    async def __aexit__(self, *exc):
        return False


def _drain(agen):
    async def _run_it():
        return [x async for x in agen]
    return asyncio.run(_run_it())


def test_anthropic_stream_retried_ohne_temperature(monkeypatch):
    calls: list[dict] = []

    class FakeMessages:
        def stream(self, **kwargs):
            calls.append(kwargs)
            return _FakeManager(should_raise="temperature" in kwargs)

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.llm._anthropic import anthropic_stream
    _drain(anthropic_stream(
        key="sk-ant-test", messages=[{"role": "user", "content": "hi"}],
        model="claude-opus-4-8", temperature=1.0, max_tokens=1024,
    ))

    assert len(calls) == 2
    assert "temperature" in calls[0]
    assert "temperature" not in calls[1]


def test_minimax_stream_retried_ohne_temperature(monkeypatch):
    calls: list[dict] = []

    class FakeMessages:
        def stream(self, **kwargs):
            calls.append(kwargs)
            return _FakeManager(should_raise="temperature" in kwargs)

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)

    from hydrahive.llm._anthropic import minimax_stream
    _drain(minimax_stream(
        api_key="key", messages=[{"role": "user", "content": "hi"}],
        model="MiniMax-M2", temperature=1.0, max_tokens=1024,
    ))

    assert len(calls) == 2 and "temperature" not in calls[1]
