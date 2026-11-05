"""Codex-Stream: stehende Verbindung wird nach kurzer Frist erkannt statt nach 300 s.

Befund hydratest 5.11.2026 (Container hinter Heimrouter): Von 12 kurzen Anfragen blieben 2 stehen – einmal ohne jedes
Ereignis, einmal nach `response.created` – bis zum 300-s-Lesezeitlimit von httpx, danach Wiederholung und Fallback:
mehrere Minuten für einen Aussetzer. Gemessen im selben Lauf: normale Läufe liefern das erste Ereignis nach ~1 s, die
größte Lücke bei `reasoning_effort=high` war 4,3 s.

Zwei Fristen: bis zum ERSTEN Ereignis und zwischen zwei Ereignissen. Wer langsam, aber stetig liefert, wird nie
abgebrochen (Gesamtdauer zählt nicht).
"""
from __future__ import annotations

import asyncio
import json
import time

import httpx
import pytest

from hydrahive.runner import _codex_provider as cp

DONE = {"type": "response.completed", "response": {"usage": {"input_tokens": 5, "output_tokens": 1}}}


def _line(ev: dict) -> bytes:
    return f"data: {json.dumps(ev)}\n\n".encode()


class _Slow(httpx.AsyncByteStream):
    """Liefert Stücke nach vorgegebenen Pausen; `closed` zeigt, ob der Kern die Verbindung freigegeben hat."""

    def __init__(self, plan: list[tuple[float, bytes]], state: dict) -> None:
        self.plan, self.state = plan, state

    async def __aiter__(self):
        for pause, chunk in self.plan:
            await asyncio.sleep(pause)
            yield chunk

    async def aclose(self) -> None:
        self.state["closed"] = True


@pytest.fixture
def slow(monkeypatch):
    state: dict = {"closed": False}
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 0.3)
    monkeypatch.setattr(cp, "_GAP_TIMEOUT", 0.5)

    def run(plan: list[tuple[float, bytes]]):
        state["closed"] = False

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, stream=_Slow(plan, state), headers={"content-type": "text/event-stream"})

        real = httpx.AsyncClient

        def fake_client(*a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            return real(*a, **kw)
        monkeypatch.setattr(cp.httpx, "AsyncClient", fake_client)

        async def go():
            t = time.monotonic()
            try:
                evs = [e async for e in cp.codex_stream(access_token="t", account_id="a", model="gpt-5.6-luna",
                                                        system_prompt="s", messages=[{"role": "user", "content": "hi"}],
                                                        tools=[])]
                return evs, None, time.monotonic() - t
            except Exception as exc:                     # noqa: BLE001
                return None, exc, time.monotonic() - t
        return asyncio.run(go())
    run.state = state
    return run


def test_kein_ereignis_innerhalb_der_ersten_frist_bricht_ab(slow):
    evs, exc, dt = slow([(5.0, _line(DONE))])
    assert isinstance(exc, cp.CodexStreamStall)
    assert dt < 1.5                                      # nicht 5 s abwarten, schon gar nicht 300


def test_stall_ist_ein_stream_fehler_damit_der_kern_wiederholt(slow):
    _, exc, _ = slow([(5.0, _line(DONE))])
    assert isinstance(exc, cp.CodexStreamError)          # `_call` wiederholt/fällt zurück auf diese Klasse


def test_meldung_nennt_die_phase_und_die_sekunden(slow):
    _, exc, _ = slow([(5.0, _line(DONE))])
    assert "erstes Ereignis" in str(exc) and "0.3" in str(exc)
    _, exc2, _ = slow([(0.0, _line({"type": "response.created"})), (5.0, _line(DONE))])
    assert "Pause" in str(exc2) and "0.5" in str(exc2)


def test_pause_nach_dem_ersten_ereignis_bricht_nach_der_gap_frist_ab(slow):
    evs, exc, dt = slow([(0.0, _line({"type": "response.created"})), (5.0, _line(DONE))])
    assert isinstance(exc, cp.CodexStreamStall)
    assert 0.4 < dt < 1.5                                # Gap-Frist 0,5 s, nicht die 0,3 s der ersten Frist


def test_erste_frist_gilt_nur_fuer_das_erste_ereignis(slow):
    """Erstes Ereignis nach 0,2 s (< 0,3), danach Pausen von 0,4 s (> 0,3, < 0,5): darf NICHT abbrechen."""
    evs, exc, _ = slow([(0.2, _line({"type": "response.created"})),
                        (0.4, _line({"type": "response.output_text.delta", "delta": "Hallo"})), (0.4, _line(DONE))])
    assert exc is None and evs[-1]["type"] == "message_stop"
    assert evs[-1]["blocks"] == [{"type": "text", "text": "Hallo"}]


def test_langsam_aber_stetig_wird_nie_abgebrochen(slow):
    """Gesamtdauer ~1,8 s ist länger als beide Fristen zusammen – jede Lücke ist kürzer als die Frist."""
    plan = [(0.25, _line({"type": "response.created"}))] + [
        (0.3, _line({"type": "response.output_text.delta", "delta": "x"})) for _ in range(5)] + [(0.3, _line(DONE))]
    evs, exc, dt = slow(plan)
    assert exc is None and dt > 1.5
    assert evs[-1]["blocks"] == [{"type": "text", "text": "xxxxx"}]


def test_verbindung_wird_nach_dem_abbruch_freigegeben(slow):
    slow([(5.0, _line(DONE))])
    assert slow.state["closed"] is True


def test_normaler_lauf_unveraendert(slow):
    evs, exc, dt = slow([(0.0, _line({"type": "response.output_text.delta", "delta": "Hallo"})), (0.0, _line(DONE))])
    assert exc is None and evs[-1]["blocks"] == [{"type": "text", "text": "Hallo"}] and dt < 0.5


def test_fehlerereignis_bleibt_ein_fehler_und_kein_stall(slow):
    _, exc, _ = slow([(0.0, _line({"type": "error", "code": "rate_limit_exceeded", "message": "Zu viele"}))])
    assert isinstance(exc, cp.CodexStreamError) and not isinstance(exc, cp.CodexStreamStall)
    assert "rate_limit_exceeded" in str(exc)


def test_abbruch_von_aussen_wird_nicht_verschluckt(slow, monkeypatch):
    """Stoppt der Nutzer den Lauf (Task.cancel), muss CancelledError ankommen – nicht in einen Stall umgedeutet."""
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 30.0)

    def handler(request):
        return httpx.Response(200, stream=_Slow([(10.0, _line(DONE))], slow.state), headers={"content-type": "text/event-stream"})
    real = httpx.AsyncClient
    monkeypatch.setattr(cp.httpx, "AsyncClient", lambda *a, **kw: real(*a, **{**kw, "transport": httpx.MockTransport(handler)}))

    async def go():
        async def consume():
            async for _ in cp.codex_stream(access_token="t", account_id="a", model="m", system_prompt="s",
                                           messages=[{"role": "user", "content": "hi"}], tools=[]):
                pass
        task = asyncio.create_task(consume())
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(go())


def test_standardwerte_sind_die_vereinbarten():
    assert cp._FIRST_EVENT_TIMEOUT == 30.0
    assert cp._GAP_TIMEOUT == 90.0
