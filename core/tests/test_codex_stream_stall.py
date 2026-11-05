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
    real = httpx.AsyncClient                             # einmal sichern: `run` darf mehrfach je Test aufgerufen werden
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 0.3)
    monkeypatch.setattr(cp, "_GAP_TIMEOUT", 0.5)

    def run(plan: list[tuple[float, bytes]]):
        state["closed"] = False

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, stream=_Slow(plan, state), headers={"content-type": "text/event-stream"})


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
    _, exc, _ = slow([(0.0, _line({"type": "error", "error": {"code": "rate_limit_exceeded", "message": "Zu viele"}}))])
    assert isinstance(exc, cp.CodexStreamError) and not isinstance(exc, cp.CodexStreamStall)
    assert "rate_limit_exceeded" in str(exc)


def test_abbruch_von_aussen_wird_nicht_verschluckt(slow, monkeypatch):
    """Stoppt der Nutzer den Lauf (Task.cancel), muss CancelledError ankommen – nicht in einen Stall umgedeutet."""
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 30.0)
    real = httpx.AsyncClient

    def handler(request):
        return httpx.Response(200, stream=_Slow([(10.0, _line(DONE))], slow.state), headers={"content-type": "text/event-stream"})
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
    assert cp._GAP_TIMEOUT == 45.0


# --- Phase VOR dem Antwortkopf (Messung hydratest 5.11., 30 echte Anfragen: 4 von 5 Aussetzern standen hier) --------

@pytest.fixture
def slow_header(monkeypatch):
    """Server, der den Antwortkopf erst nach `delay` Sekunden schickt."""
    real = httpx.AsyncClient
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 0.3)
    monkeypatch.setattr(cp, "_GAP_TIMEOUT", 0.5)

    def run(delay: float):
        async def handler(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(delay)
            return httpx.Response(200, content=_line({"type": "response.output_text.delta", "delta": "ok"}) + _line(DONE),
                                  headers={"content-type": "text/event-stream"})
        monkeypatch.setattr(cp.httpx, "AsyncClient",
                            lambda *a, **kw: real(*a, **{**kw, "transport": httpx.MockTransport(handler)}))

        async def go():
            t = time.monotonic()
            try:
                evs = [e async for e in cp.codex_stream(access_token="t", account_id="a", model="m", system_prompt="s",
                                                        messages=[{"role": "user", "content": "hi"}], tools=[])]
                return evs, None, time.monotonic() - t
            except Exception as exc:                     # noqa: BLE001
                return None, exc, time.monotonic() - t
        return asyncio.run(go())
    return run


def test_kopf_kommt_nicht_in_der_frist_bricht_ab(slow_header):
    evs, exc, dt = slow_header(5.0)
    assert isinstance(exc, cp.CodexStreamStall) and dt < 1.5


def test_meldung_nennt_antwortkopf(slow_header):
    _, exc, _ = slow_header(5.0)
    assert "Antwortkopf" in str(exc) and "0.3" in str(exc)


def test_kopf_rechtzeitig_normaler_lauf(slow_header):
    evs, exc, _ = slow_header(0.1)
    assert exc is None and evs[-1]["blocks"] == [{"type": "text", "text": "ok"}]


def test_kopf_frist_ist_die_erste_frist_nicht_die_pausenfrist(slow_header):
    """Kopf nach 0,4 s: länger als die erste Frist (0,3), kürzer als die Pausenfrist (0,5) → muss abbrechen."""
    _, exc, _ = slow_header(0.4)
    assert isinstance(exc, cp.CodexStreamStall)


def test_verbindung_wird_auch_beim_abbruch_vor_dem_kopf_freigegeben(monkeypatch):
    """Kein Leck: Die Frist vor dem Kopf schließt den Client (async with … `AsyncClient`) sauber."""
    closed = {"n": 0}
    real = httpx.AsyncClient
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 0.2)

    class Spy(real):
        async def __aexit__(self, *a):
            closed["n"] += 1
            return await super().__aexit__(*a)

    async def handler(request):
        await asyncio.sleep(5)
        return httpx.Response(200, content=b"")
    monkeypatch.setattr(cp.httpx, "AsyncClient", lambda *a, **kw: Spy(*a, **{**kw, "transport": httpx.MockTransport(handler)}))

    async def go():
        with pytest.raises(cp.CodexStreamStall):
            async for _ in cp.codex_stream(access_token="t", account_id="a", model="m", system_prompt="s",
                                           messages=[{"role": "user", "content": "hi"}], tools=[]):
                pass
    asyncio.run(go())
    assert closed["n"] == 1


def test_abbruch_von_aussen_vor_dem_kopf_wird_nicht_verschluckt(monkeypatch):
    monkeypatch.setattr(cp, "_FIRST_EVENT_TIMEOUT", 30.0)
    real = httpx.AsyncClient

    async def handler(request):
        await asyncio.sleep(10)
        return httpx.Response(200, content=b"")
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


def test_fehlerstatus_vor_dem_kopf_bleibt_unveraendert(monkeypatch):
    """HTTP-Fehler (hier 429) laufen weiter wie bisher als RuntimeError – die Frist fängt sie nicht ab."""
    real = httpx.AsyncClient
    monkeypatch.setattr(cp.httpx, "AsyncClient", lambda *a, **kw: real(*a, **{
        **kw, "transport": httpx.MockTransport(lambda r: httpx.Response(429, content=b"zu viele"))}))

    async def go():
        with pytest.raises(RuntimeError) as e:
            async for _ in cp.codex_stream(access_token="t", account_id="a", model="m", system_prompt="s",
                                           messages=[{"role": "user", "content": "hi"}], tools=[]):
                pass
        assert not isinstance(e.value, cp.CodexStreamStall) and "429" in str(e.value)
    asyncio.run(go())


# --- Freigabe der Antwort (Leck-Schutz) ------------------------------------------------------------------------

class _TrackedResponse(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes], state: dict) -> None:
        self.chunks, self.state = chunks, state

    async def __aiter__(self):
        for c in self.chunks:
            yield c

    async def aclose(self) -> None:
        self.state["closed"] = self.state.get("closed", 0) + 1


def _run_tracked(monkeypatch, chunks: list[bytes], *, consume_all: bool = True):
    state: dict = {}
    real = httpx.AsyncClient
    monkeypatch.setattr(cp.httpx, "AsyncClient", lambda *a, **kw: real(*a, **{**kw, "transport": httpx.MockTransport(
        lambda r: httpx.Response(200, stream=_TrackedResponse(chunks, state), headers={"content-type": "text/event-stream"}))}))

    async def go():
        err = None
        try:
            async for _ in cp.codex_stream(access_token="t", account_id="a", model="m", system_prompt="s",
                                           messages=[{"role": "user", "content": "hi"}], tools=[]):
                pass
        except Exception as exc:                         # noqa: BLE001
            err = exc
        return err
    return asyncio.run(go()), state


def test_antwort_wird_nach_normalem_ende_geschlossen(monkeypatch):
    err, state = _run_tracked(monkeypatch, [_line({"type": "response.output_text.delta", "delta": "x"}), _line(DONE)])
    assert err is None and state.get("closed") == 1


def test_antwort_wird_bei_fehlerereignis_geschlossen(monkeypatch):
    err, state = _run_tracked(monkeypatch, [_line({"type": "error", "error": {"code": "x", "message": "kaputt"}})])
    assert isinstance(err, cp.CodexStreamError) and state.get("closed") == 1


def test_antwort_wird_bei_stream_ohne_abschluss_geschlossen(monkeypatch):
    err, state = _run_tracked(monkeypatch, [_line({"type": "response.output_text.delta", "delta": "x"})])
    assert isinstance(err, cp.CodexStreamError) and "ohne Abschluss" in str(err) and state.get("closed") == 1
