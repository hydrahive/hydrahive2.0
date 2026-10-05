"""Codex-Stream: Fehler-Events werden zur Fehlermeldung statt zur leeren Antwort.

Befund VPS 04.10.2026: Ein Lauf auf openai-codex/gpt-5.6-sol endete mit
0 Blöcken, der Nutzer sah nur "leere Antwort". codex_stream wertete Fehler-
Events nicht aus und lieferte auch ohne response.completed ein message_stop.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from hydrahive.runner import _codex_provider as cp


def _sse(*events: dict) -> bytes:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events).encode()


@pytest.fixture
def stream(monkeypatch):
    """codex_stream gegen einen gefälschten Codex-Server laufen lassen."""
    body: dict = {"data": b""}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body["data"], headers={"content-type": "text/event-stream"})

    real = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(cp.httpx, "AsyncClient", fake_client)

    def run(*events: dict) -> list[dict]:
        body["data"] = _sse(*events)

        async def go():
            return [ev async for ev in cp.codex_stream(
                access_token="t", account_id="a", model="gpt-5.6-sol",
                system_prompt="s", messages=[{"role": "user", "content": "hi"}], tools=[],
            )]
        return asyncio.run(go())

    return run


def test_normal_text_still_works(stream):
    evs = stream(
        {"type": "response.output_text.delta", "delta": "Hallo"},
        {"type": "response.completed", "response": {"usage": {"input_tokens": 5, "output_tokens": 1}}},
    )
    stop = evs[-1]
    assert stop["type"] == "message_stop"
    assert stop["blocks"] == [{"type": "text", "text": "Hallo"}]
    assert stop["output_tokens"] == 1


def test_error_event_raises_with_message(stream):
    with pytest.raises(cp.CodexStreamError) as exc:
        stream({"type": "error", "code": "rate_limit_exceeded", "message": "Too many requests",
                "error": {"code": "rate_limit_exceeded", "message": "Too many requests"}})
    assert "rate_limit_exceeded" in str(exc.value)
    assert "Too many requests" in str(exc.value)


def test_response_failed_raises(stream):
    with pytest.raises(cp.CodexStreamError) as exc:
        stream({"type": "response.failed", "response": {
            "status": "failed", "error": {"code": "server_error", "message": "Upstream kaputt"}}})
    assert "Upstream kaputt" in str(exc.value)


def test_response_incomplete_names_reason(stream):
    with pytest.raises(cp.CodexStreamError) as exc:
        stream({"type": "response.incomplete", "response": {
            "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}})
    assert "max_output_tokens" in str(exc.value)


def test_stream_without_completed_raises(stream):
    """Der eigentliche Leer-Fall: nichts kommt, kein Abschluss → Fehler statt leerer Antwort."""
    with pytest.raises(cp.CodexStreamError):
        stream({"type": "response.created"}, {"type": "response.in_progress"})


def test_codex_call_propagates(stream, monkeypatch):
    stream  # Fixture aktiviert den Fake-Server
    body = _sse({"type": "error", "error": {"code": "x", "message": "kaputt"}})

    def handler(request):
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    real = httpx.AsyncClient
    monkeypatch.setattr(cp.httpx, "AsyncClient", lambda *a, **k: real(*a, **{**k, "transport": httpx.MockTransport(handler)}))
    with pytest.raises(cp.CodexStreamError):
        asyncio.run(cp.codex_call(access_token="t", account_id="a", model="m",
                                  system_prompt="s", messages=[{"role": "user", "content": "hi"}], tools=[]))
