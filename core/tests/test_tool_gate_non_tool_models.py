"""Tool-Gate: Modelle ohne Function-Calling bekommen keine tool_schemas.

Hintergrund (Bug den till gefunden hat):
- Der Runner schickte IMMER tool_schemas ans Modell, auch wenn das Modell laut
  Catalog tool_use=False hat (z.B. lokale Ollama-Modelle ohne Tool-Capability).
- Folge: das Modell kann keine echten Tool-Calls emittieren und erfindet sie als
  Text-JSON. HydraHive fuehrt das (korrekt) NICHT aus -> rohes JSON landet
  stumpf im Chat statt einer Antwort.

Fix-Vertrag (hier als RED-Tests festgenagelt):
1. model_supports_tools() liest zuerst den Registry-Cache (dort landen ueber
   catalog_for_providers auch die Ollama-Modelle mit ihrer /api/show-
   Capability), dann statische METADATA, sonst True.
2. call_with_stream_or_fallback filtert die Tools PRO MODELL — auch fuer
   Fallback-Modelle, die eine andere Tool-Faehigkeit haben koennen.
3. Unbekannte Modelle behalten Tools (fail-open).

WICHTIG zur Quellenwahl: Ollama-Modelle stehen NICHT in METADATA und auch NICHT
im catalog._cache — catalog_for_providers behandelt Ollama in einem Sonderzweig,
der _cached_fetch komplett umgeht. Nur die Registry sieht beide Welten.

Alle Importe lazy in der Funktion (Test-Isolation: settings-Singleton nicht
zur Collection-Zeit festnageln).
"""
from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    from hydrahive.llm import registry
    registry.invalidate()
    yield
    registry.invalidate()


def _seed_registry(*entries: tuple[str, bool | None]) -> None:
    """Setzt den Registry-Cache direkt (kein Netzwerk)."""
    import time

    from hydrahive.llm import registry
    built = [
        registry.ModelEntry(
            id=mid, provider="x", label=mid, purposes=frozenset({"chat"}),
            tool_use=tu,
        )
        for mid, tu in entries
    ]
    registry._cache = (time.monotonic(), built)


# --- 1. model_supports_tools: die SSOT-Aufloesung ---------------------------

def test_metadata_modell_ohne_toolsupport_wird_erkannt():
    """abab5.5-chat steht mit tool_use=False in METADATA."""
    from hydrahive.llm.tool_support import model_supports_tools
    assert model_supports_tools("abab5.5-chat") is False


def test_metadata_modell_mit_toolsupport_bleibt_true():
    from hydrahive.llm.tool_support import model_supports_tools
    assert model_supports_tools("claude-sonnet-4-5") is True


def test_unbekanntes_modell_behaelt_tools_fail_open():
    """Fail-open: lieber Tools an ein Modell das sie nicht kann (sichtbar,
    harmlos) als einen funktionierenden Agenten stumm entmachten."""
    from hydrahive.llm.tool_support import model_supports_tools
    assert model_supports_tools("irgendein/unbekanntes-modell") is True


def test_metadata_lookup_auch_ohne_provider_prefix():
    """'openrouter/abab5.5-chat' muss auf den METADATA-Key ohne Prefix fallen."""
    from hydrahive.llm.tool_support import model_supports_tools
    assert model_supports_tools("openrouter/abab5.5-chat") is False


def test_ollama_capability_aus_registry():
    """DER KERNFALL: Ollama-Modelle stehen NICHT in METADATA. Ihre Tool-
    Faehigkeit kommt aus /api/show und landet ueber den Catalog in der
    Registry. Ein reiner METADATA-Lookup wuerde diesen Bug-Fall verfehlen."""
    from hydrahive.llm.tool_support import model_supports_tools

    _seed_registry(("ollama/gemma4:27b", False), ("ollama/qwen3:14b", True))
    assert model_supports_tools("ollama/gemma4:27b") is False
    assert model_supports_tools("ollama/qwen3:14b") is True


def test_registry_hat_vorrang_vor_metadata():
    """Wenn ein Modell live als tool-los gemeldet wird, gewinnt das gegen eine
    veraltete statische METADATA-Angabe."""
    from hydrahive.llm.tool_support import model_supports_tools

    _seed_registry(("claude-sonnet-4-5", False))
    assert model_supports_tools("claude-sonnet-4-5") is False


def test_registry_ohne_toolinfo_faellt_auf_metadata_zurueck():
    """tool_use=None in der Registry (Provider meldet nichts) darf das Modell
    nicht faelschlich entmachten — METADATA entscheidet."""
    from hydrahive.llm.tool_support import model_supports_tools

    _seed_registry(("abab5.5-chat", None), ("claude-sonnet-4-5", None))
    assert model_supports_tools("abab5.5-chat") is False
    assert model_supports_tools("claude-sonnet-4-5") is True


def test_kalter_cache_faellt_auf_metadata_zurueck():
    """Kein Netzwerk-Call im heissen Pfad: leerer Cache = METADATA/Default."""
    from hydrahive.llm.tool_support import model_supports_tools
    assert model_supports_tools("abab5.5-chat") is False
    assert model_supports_tools("claude-sonnet-4-5") is True


# --- 2. Das Gate im Runner --------------------------------------------------

class _Recorder:
    """Faengt die tools ab, die tatsaechlich am Provider ankommen."""

    def __init__(self):
        self.seen: list[tuple[str, list]] = []

    async def stream(self, **kwargs):
        self.seen.append((kwargs["model"], kwargs["tools"]))
        yield {"type": "message_start"}
        yield {
            "type": "message_stop", "stop_reason": "end_turn",
            "blocks": [{"type": "text", "text": "ok"}],
            "input_tokens": 1, "output_tokens": 1,
            "cache_creation_tokens": 0, "cache_read_tokens": 0,
        }


_TOOLS = [{"name": "shell_exec", "description": "x", "input_schema": {}}]


def _drain(models, monkeypatch, rec):
    from hydrahive.runner import _call
    monkeypatch.setattr(_call, "stream_with_tools", rec.stream)

    async def go():
        out = []
        async for ev in _call.call_with_stream_or_fallback(
            models=models, system_prompt="s", messages=[{"role": "user", "content": "hi"}],
            tools=_TOOLS, temperature=0.7, max_tokens=100,
        ):
            out.append(ev)
        return out

    return asyncio.run(go())


def test_gate_entfernt_tools_bei_modell_ohne_toolsupport(monkeypatch):
    rec = _Recorder()
    _drain(["abab5.5-chat"], monkeypatch, rec)
    model, tools = rec.seen[0]
    assert model == "abab5.5-chat"
    assert tools == [], "Modell ohne Function-Calling darf keine tool_schemas sehen"


def test_gate_laesst_tools_bei_faehigem_modell_durch(monkeypatch):
    rec = _Recorder()
    _drain(["claude-sonnet-4-5"], monkeypatch, rec)
    _, tools = rec.seen[0]
    assert tools == _TOOLS


def test_gate_greift_pro_modell_in_der_fallback_kette(monkeypatch):
    """Das Gate darf nicht einmalig pro Session entschieden werden: die
    Fallback-Kette kann auf ein Modell mit anderer Tool-Faehigkeit wechseln."""
    from hydrahive.runner import _call

    calls: list[tuple[str, list]] = []

    async def failing_stream(**kwargs):
        raise RuntimeError("stream kaputt")
        yield  # pragma: no cover

    # Primary schlaegt fehl -> Failover aufs zweite Modell. Beide Modelle
    # muessen individuell gegatet werden.
    async def fake_call_with_tools(**kwargs):
        calls.append((kwargs["model"], kwargs["tools"]))
        if kwargs["model"] == "abab5.5-chat":
            raise TimeoutError("primary down")
        return [{"type": "text", "text": "ok"}], "end_turn", {}

    monkeypatch.setattr(_call, "stream_with_tools", failing_stream)
    monkeypatch.setattr(_call, "call_with_tools", fake_call_with_tools)
    monkeypatch.setattr(_call, "should_failover", lambda e: True)

    async def go():
        async for _ in _call.call_with_stream_or_fallback(
            models=["abab5.5-chat", "claude-sonnet-4-5"], system_prompt="s",
            messages=[{"role": "user", "content": "hi"}], tools=_TOOLS,
            temperature=0.7, max_tokens=100,
        ):
            pass

    asyncio.run(go())
    assert len(calls) == 2, f"beide Modelle muessen versucht worden sein: {calls}"
    assert calls[0] == ("abab5.5-chat", []), "tool-loses Primary: keine Tools"
    assert calls[1] == ("claude-sonnet-4-5", _TOOLS), "faehiges Fallback: Tools bleiben"


def test_gate_veraendert_die_uebergebene_tools_liste_nicht(monkeypatch):
    """Kein In-Place-Mutieren: der Runner baut tool_schemas EINMAL und
    wiederverwendet sie ueber alle Iterationen."""
    rec = _Recorder()
    original = list(_TOOLS)
    _drain(["abab5.5-chat"], monkeypatch, rec)
    assert _TOOLS == original
