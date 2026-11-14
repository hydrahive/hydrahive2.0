"""Modellkette im LLM-Aufruf (Spec agent-templates.md Kap. 8, Plan E1 T2–T6).

Vertrag:
- Timeout/Verbindungsabbruch: nach den Wiederholversuchen auf frischer Verbindung kommt das NÄCHSTE Modell dran.
- Anbieterfehler (429, Quota, Overload, Auth) vor dem ersten Text: nächstes Modell wird GESTREAMT.
- Leere Antwort (kein Text, kein Werkzeug): dasselbe Modell einmal erneut, dann nächstes Modell.
  Beim letzten Modell bleibt es bei der leeren Antwort (der Runner meldet sie wie bisher).
- Nach gesendetem Text wird nicht auf ein anderes Modell gestreamt (sonst doppelter Text).
- Anbieterfehler sperren das Modell kurz; gesperrte Modelle werden übersprungen, außer alle sind gesperrt.
- Jeder Wechsel wird als `ModelSwitch` gemeldet und steht in `CallResult.switches`.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from hydrahive.runner import _call
from hydrahive.runner import _model_cooldown as cooldown
from hydrahive.runner.events import ModelSwitch

A, B, C = "claude-opus-5-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"


def ok(text: str):
    return [{"type": "message_start"}, {"type": "text_delta", "text": text},
            {"type": "message_stop", "blocks": [{"type": "text", "text": text}], "stop_reason": "end_turn",
             "input_tokens": 1, "output_tokens": 1}]


EMPTY = [{"type": "message_start"},
         {"type": "message_stop", "blocks": [{"type": "thinking", "thinking": "…"}], "stop_reason": "end_turn"}]


class Fake:
    """Skript je Modell: Liste von Stream-Versuchen (Ereignisliste oder Exception)."""

    def __init__(self, streams: dict, calls: dict | None = None) -> None:
        self.streams = {m: list(v) for m, v in streams.items()}
        self.calls = {m: list(v) for m, v in (calls or {}).items()}
        self.stream_log: list[str] = []
        self.call_log: list[str] = []

    async def stream(self, **kw):
        model = kw["model"]
        self.stream_log.append(model)
        script = self.streams.get(model) or []
        item = script.pop(0) if script else RuntimeError(f"kein Skript für {model}")
        if isinstance(item, BaseException):
            raise item
        for ev in item:
            yield ev

    async def call(self, **kw):
        model = kw["model"]
        self.call_log.append(model)
        script = self.calls.get(model) or []
        item = script.pop(0) if script else ([{"type": "text", "text": f"FB-{model}"}], "end_turn", {})
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    async def no_sleep(_s):
        return None
    monkeypatch.setattr(_call.asyncio, "sleep", no_sleep)
    cooldown.reset()
    yield
    cooldown.reset()


@pytest.fixture
def fake(monkeypatch):
    def make(streams, calls=None):
        f = Fake(streams, calls)
        monkeypatch.setattr(_call, "stream_with_tools", f.stream)
        monkeypatch.setattr(_call, "call_with_tools", f.call)
        return f
    return make


def run(models, **extra):
    async def go():
        return [ev async for ev in _call.call_with_stream_or_fallback(
            models=models, system_prompt="s", messages=[], tools=[], temperature=0.0, max_tokens=10, **extra)]
    return asyncio.run(go())


def result(events) -> _call.CallResult:
    return [e for e in events if isinstance(e, _call.CallResult)][-1]


def switches(events) -> list[tuple[str, str, str]]:
    return [(e.from_model, e.to_model, e.reason) for e in events if isinstance(e, ModelSwitch)]


# --- T2: Timeout / Verbindungsabbruch ------------------------------------------------------------------------------

def test_timeouts_auf_a_dann_antwortet_b(fake):
    t = httpx.ReadTimeout("")
    f = fake({A: [t] * 5, B: [ok("B")]})
    ev = run([A, B])
    assert result(ev).model == B and result(ev).blocks == [{"type": "text", "text": "B"}]
    assert switches(ev) == [(A, B, "timeout")]
    assert f.stream_log == [A] * 5 + [B] and f.call_log == []


def test_timeout_nur_ein_modell_wirft_wie_bisher(fake):
    t = httpx.ReadTimeout("")
    fake({A: [t] * 5}, calls={A: [t] * 5})
    with pytest.raises(httpx.ReadTimeout):
        run([A])


def test_nicht_streaming_timeout_wechselt_ebenfalls(fake):
    from hydrahive.runner.llm_bridge_stream import StreamingNotSupported
    f = fake({A: [StreamingNotSupported("nein")]}, calls={A: [httpx.ConnectTimeout("")] * 5})
    ev = run([A, B])
    assert result(ev).model == B
    assert f.call_log == [A] * 5 + [B]
    assert switches(ev) == [(A, B, "timeout")]


# --- T3: leere Antwort ---------------------------------------------------------------------------------------------

def test_leer_dann_nochmal_dasselbe_modell(fake):
    f = fake({A: [EMPTY, ok("A2")]})
    ev = run([A, B])
    assert result(ev).model == A and f.stream_log == [A, A]
    assert switches(ev) == []


def test_zweimal_leer_dann_naechstes_modell(fake):
    f = fake({A: [EMPTY, EMPTY], B: [ok("B")]})
    ev = run([A, B])
    assert result(ev).model == B and f.stream_log == [A, A, B]
    assert switches(ev) == [(A, B, "empty")]


def test_letztes_modell_leer_bleibt_leer(fake):
    f = fake({A: [EMPTY, EMPTY]})
    ev = run([A])
    assert result(ev).model == A and f.stream_log == [A, A]      # ein zweiter Versuch, dann bleibt es leer
    assert not any(b.get("type") == "text" for b in result(ev).blocks)


def test_einzelnes_modell_leer_dann_antwort(fake):
    f = fake({A: [EMPTY, ok("A2")]})
    assert result(run([A])).blocks == [{"type": "text", "text": "A2"}] and f.stream_log == [A, A]


def test_werkzeugaufruf_ist_nicht_leer(fake):
    tool = [{"type": "message_stop", "stop_reason": "tool_use",
             "blocks": [{"type": "tool_use", "id": "1", "name": "x", "input": {}}]}]
    f = fake({A: [tool]})
    assert result(run([A, B])).model == A and f.stream_log == [A]


# --- T4: Kette beim Streaming --------------------------------------------------------------------------------------

def test_429_vor_text_streamt_das_naechste_modell(fake):
    f = fake({A: [RuntimeError("Error 429: Too Many Requests")] * 2, B: [ok("B")]})
    ev = run([A, B])
    assert result(ev).model == B and B in f.stream_log and f.call_log == []
    assert switches(ev) == [(A, B, "rate_limit")]


def test_drei_stufen(fake):
    f = fake({A: [RuntimeError("insufficient quota")] * 2, B: [RuntimeError("overloaded")] * 2, C: [ok("C")]})
    ev = run([A, B, C])
    assert result(ev).model == C
    assert switches(ev) == [(A, B, "quota"), (B, C, "overload")]
    assert f.call_log == []


def test_nach_gesendetem_text_kein_stream_auf_anderes_modell(fake, monkeypatch):
    async def text_then_429(**kw):
        yield {"type": "message_start"}
        yield {"type": "text_delta", "text": "Hal"}
        raise RuntimeError("Error 429")
    f = Fake({}, calls={A: [([{"type": "text", "text": "FB"}], "end_turn", {})]})
    monkeypatch.setattr(_call, "stream_with_tools", text_then_429)
    monkeypatch.setattr(_call, "call_with_tools", f.call)
    ev = run([A, B])
    assert not any(isinstance(e, ModelSwitch) and e.reason == "rate_limit" and e.to_model == B
                   for e in ev[:3])
    assert f.call_log[0] == A          # wie bisher: Nicht-Streaming auf demselben Modell


def test_unbekannter_fehler_wechselt_nicht(fake):
    f = fake({A: [ValueError("json decode error")] * 2}, calls={A: [ValueError("json decode error")]})
    with pytest.raises(ValueError):
        run([A, B])
    assert B not in f.stream_log and B not in f.call_log


# --- T5: Sperrzeit -------------------------------------------------------------------------------------------------

def test_quota_sperrt_modell_beim_naechsten_aufruf(fake):
    fake({A: [RuntimeError("insufficient quota")] * 2, B: [ok("B1")]})
    run([A, B])
    f = fake({B: [ok("B2")]})
    ev = run([A, B])
    assert f.stream_log == [B] and result(ev).model == B
    assert switches(ev) == [(A, B, "cooldown")]


def test_timeout_sperrt_nicht(fake):
    fake({A: [httpx.ReadTimeout("")] * 5, B: [ok("B")]})
    run([A, B])
    f = fake({A: [ok("A")]})
    assert result(run([A, B])).model == A and f.stream_log == [A]


def test_alle_gesperrt_trotzdem_versuchen(fake):
    cooldown.mark_down(A, 300)
    cooldown.mark_down(B, 300)
    f = fake({A: [ok("A")]})
    assert result(run([A, B])).model == A and f.stream_log == [A]


def test_sperre_laeuft_ab():
    cooldown.mark_down(A, 300, now=1000.0)
    assert cooldown.is_down(A, now=1299.0)
    assert not cooldown.is_down(A, now=1300.0)


def test_sperrzeit_null_sperrt_nicht(fake):
    fake({A: [RuntimeError("insufficient quota")] * 2, B: [ok("B")]})
    run([A, B], cooldown_seconds=0)
    assert not cooldown.is_down(A)


# --- T6: Wechsel im Ergebnis ---------------------------------------------------------------------------------------

def test_wechsel_steht_im_ergebnis(fake):
    fake({A: [RuntimeError("Error 429")] * 2, B: [ok("B")]})
    assert result(run([A, B])).switches == [{"from_model": A, "to_model": B, "reason": "rate_limit"}]


def test_ohne_wechsel_leer(fake):
    fake({A: [ok("A")]})
    assert result(run([A, B])).switches == []
