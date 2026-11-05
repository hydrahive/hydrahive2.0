"""LLM-Call: stehende Codex-Verbindung (CodexStreamStall) wird mehrfach auf frischer Verbindung wiederholt.

Messung hydratest 5.11.2026: Ein Stall betrifft die Verbindung, nicht die Anfrage – der unmittelbare Wiederholversuch
ist in ~80 % der Fälle sofort erfolgreich (erstes Ereignis nach ~1 s). Bisher gab es nur 3 Versuche (2× Stream, 1×
Non-Streaming); drei Aussetzer hintereinander ließen den Lauf scheitern (1 von 60 echten Läufen).

Vertrag:
- Nach einem Stall bis zu `STALL_ATTEMPTS` (5) Stream-Versuche, jeweils neue Verbindung; Pause kurz.
- Andere Fehler behalten genau das bisherige Verhalten (1 Wiederholung, dann Fallback).
- Wurde schon Text an die Oberfläche geliefert, wird NICHT wiederholt (sonst doppelter Text).
- Sind alle Versuche verbraucht, folgt wie bisher der Fallback auf Non-Streaming.
- Abbruch von außen läuft unverändert durch.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.runner import _call
from hydrahive.runner._codex_provider import CodexStreamError, CodexStreamStall

MODEL = ["openai-codex/gpt-5.6-luna"]
STALL = CodexStreamStall("Codex-Stream steht: Antwortkopf nach 30 s noch nicht da")
GOOD = [{"type": "message_start"}, {"type": "text_delta", "text": "Hallo"},
        {"type": "message_stop", "blocks": [{"type": "text", "text": "Hallo"}], "stop_reason": "end_turn",
         "input_tokens": 3, "output_tokens": 1}]


class Fake:
    def __init__(self, script: list) -> None:
        self.script = list(script)            # je Stream-Versuch: Liste von Ereignissen, Exception-Instanz oder ("text-dann-fehler", exc)
        self.stream_calls = 0
        self.fallback_calls = 0
        self.fallback_result = ([{"type": "text", "text": "FB"}], "end_turn", {"input_tokens": 1, "output_tokens": 1})
        self.fallback_error: Exception | None = None

    async def stream(self, **kw):
        self.stream_calls += 1
        item = self.script.pop(0) if self.script else STALL
        if isinstance(item, Exception):
            raise item
        if isinstance(item, tuple):               # ("text-dann-fehler", exc): erst Text, dann Fehler
            yield {"type": "message_start"}
            yield {"type": "text_delta", "text": "Hal"}
            raise item[1]
        for ev in item:
            yield ev

    async def call(self, **kw):
        self.fallback_calls += 1
        if self.fallback_error:
            raise self.fallback_error
        return self.fallback_result


@pytest.fixture
def fake(monkeypatch):
    async def no_sleep(_s):
        return None
    monkeypatch.setattr(_call.asyncio, "sleep", no_sleep)

    def make(*script):
        f = Fake(script)
        monkeypatch.setattr(_call, "stream_with_tools", f.stream)
        monkeypatch.setattr(_call, "call_with_tools", f.call)
        return f
    return make


def run(models=MODEL):
    async def go():
        out = []
        async for ev in _call.call_with_stream_or_fallback(models=models, system_prompt="s", messages=[], tools=[],
                                                           temperature=0.0, max_tokens=10):
            out.append(ev)
        return out
    return asyncio.run(go())


def result(events):
    return [e for e in events if isinstance(e, _call.CallResult)][-1]


def test_standardwert():
    assert _call.STALL_ATTEMPTS == 5


def test_ein_stall_dann_erfolg_ohne_fallback(fake):
    f = fake(STALL, GOOD)
    assert result(run()).blocks == [{"type": "text", "text": "Hallo"}]
    assert f.stream_calls == 2 and f.fallback_calls == 0


def test_drei_staelle_dann_erfolg_ohne_fallback(fake):
    """Der Fall aus Lauf 43: bisher scheiterte er hier (2 Streams + 1 Fallback)."""
    f = fake(STALL, STALL, STALL, GOOD)
    assert result(run()).blocks == [{"type": "text", "text": "Hallo"}]
    assert f.stream_calls == 4 and f.fallback_calls == 0


def test_genau_fuenf_stream_versuche_danach_fallback(fake):
    f = fake(STALL, STALL, STALL, STALL, STALL)
    assert result(run()).blocks == [{"type": "text", "text": "FB"}]
    assert f.stream_calls == 5 and f.fallback_calls == 1


def test_fallback_scheitert_ebenfalls_fehler_kommt_an(fake):
    f = fake(*[STALL] * 5)
    f.fallback_error = STALL
    with pytest.raises(CodexStreamStall):
        run()
    assert f.stream_calls == 5 and f.fallback_calls == 1


def test_anderer_fehler_nur_eine_wiederholung_wie_bisher(fake):
    f = fake(RuntimeError("Verbindung getrennt"), RuntimeError("Verbindung getrennt"), GOOD)
    assert result(run()).blocks == [{"type": "text", "text": "FB"}]
    assert f.stream_calls == 2 and f.fallback_calls == 1


def test_gemischt_stall_dann_anderer_fehler_dann_fallback(fake):
    """Ein Stall verlängert nicht beliebig: nach einem anderen Fehler gilt dessen Regel (Wiederholung nur wenn noch keine)."""
    f = fake(STALL, RuntimeError("kaputt"), GOOD)
    run()
    assert f.stream_calls in (2, 3) and f.stream_calls < 5


def test_nach_text_wird_nicht_wiederholt(fake):
    f = fake(("text-dann-fehler", STALL), GOOD)
    run()
    assert f.stream_calls == 1 and f.fallback_calls == 1


def test_stall_ist_ein_stream_fehler_typ(fake):
    assert isinstance(STALL, CodexStreamError)


def test_pause_zwischen_stall_versuchen_ist_kurz(monkeypatch):
    waits: list[float] = []

    async def spy(s):
        waits.append(s)
    monkeypatch.setattr(_call.asyncio, "sleep", spy)
    f = Fake([STALL, STALL, STALL, GOOD])
    monkeypatch.setattr(_call, "stream_with_tools", f.stream)
    monkeypatch.setattr(_call, "call_with_tools", f.call)
    run()
    assert len(waits) == 3 and all(w <= 1.5 for w in waits)


def test_abbruch_von_aussen_wird_nicht_wiederholt(monkeypatch):
    async def cancelled(**kw):
        raise asyncio.CancelledError()
        yield
    monkeypatch.setattr(_call, "stream_with_tools", cancelled)
    with pytest.raises(asyncio.CancelledError):
        run()


def test_modell_ohne_erlaubnis_wird_nicht_wiederholt(monkeypatch, fake):
    from hydrahive.runner._codex_provider import CodexModelNotAllowed
    f = fake(CodexModelNotAllowed("nicht verfügbar"), GOOD)
    with pytest.raises(CodexModelNotAllowed):
        run()
    assert f.stream_calls == 1


def test_erfolg_beim_ersten_mal_unveraendert(fake):
    f = fake(GOOD)
    assert result(run()).blocks == [{"type": "text", "text": "Hallo"}]
    assert f.stream_calls == 1 and f.fallback_calls == 0


def test_streaming_nicht_unterstuetzt_geht_direkt_in_den_fallback(fake):
    from hydrahive.runner.llm_bridge_stream import StreamingNotSupported
    f = fake(StreamingNotSupported("kein Streaming"))
    assert result(run()).blocks == [{"type": "text", "text": "FB"}]
    assert f.stream_calls == 1 and f.fallback_calls == 1
