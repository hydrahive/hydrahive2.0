"""Tests für _with_cache_breakpoint — TTL-Verhalten.

Geschichte: 1h-TTL wurde getestet (commit b8ca92a + 0a648b3) und verworfen.
Anthropic-Cache wird auch innerhalb der 5min server-side evictet (LRU bei
Storage-Druck), 1h-cache_creation kostet aber 2× — netto teurer.
"""
from __future__ import annotations

# Seit #200 single-source in _anthropic_payload — beide Pfade nutzen dieselbe Funktion.
from hydrahive.runner._anthropic_payload import (
    with_cache_breakpoint as backend_breakpoint,
    with_cache_breakpoint as stream_breakpoint,
)


def _make_messages() -> list[dict]:
    return [
        {"role": "user", "content": [{"type": "text", "text": "Hi"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "user", "content": [{"type": "text", "text": "Next"}]},
    ]


def test_marker_auf_letzter_message():
    """Quelle: claude.ts:3089 — default markerIndex = messages.length - 1."""
    msgs = backend_breakpoint(_make_messages())
    # messages[-1] (letzte user-message "Next") hat cache_control
    cache_ctl = msgs[-1]["content"][-1].get("cache_control")
    assert cache_ctl is not None
    assert cache_ctl["type"] == "ephemeral"
    # 5m ist Anthropic-Default — kein ttl-Feld
    assert "ttl" not in cache_ctl
    # messages[-2] hat KEIN cache_control
    assert "cache_control" not in msgs[-2]["content"][-1]


def test_stream_marker_auf_letzter_message():
    msgs = stream_breakpoint(_make_messages())
    cache_ctl = msgs[-1]["content"][-1].get("cache_control")
    assert cache_ctl is not None
    assert cache_ctl["type"] == "ephemeral"
    assert "ttl" not in cache_ctl


def test_explicit_1h_setzt_ttl_feld():
    msgs = backend_breakpoint(_make_messages(), ttl="1h")
    cache_ctl = msgs[-1]["content"][-1].get("cache_control")
    assert cache_ctl["type"] == "ephemeral"
    assert cache_ctl["ttl"] == "1h"


def test_leere_messages():
    out = backend_breakpoint([])
    assert out == []


def test_einzelne_message_bekommt_marker():
    """Anders als vorher: auch eine einzelne Message kann den marker bekommen."""
    one = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
    out = backend_breakpoint(one)
    assert out[-1]["content"][-1].get("cache_control") == {"type": "ephemeral"}


def test_string_content_wird_zu_block_liste():
    """Falls eine Message content als String hat (alte API-Form), wird's ge-blockt."""
    msgs = [{"role": "user", "content": "plain text"}]
    out = backend_breakpoint(msgs)
    assert isinstance(out[-1]["content"], list)
    assert out[-1]["content"][-1].get("cache_control") == {"type": "ephemeral"}


def test_ttl_durchgereicht_an_alle_provider():
    backend_ctl = backend_breakpoint(_make_messages())[-1]["content"][-1]["cache_control"]
    stream_ctl = stream_breakpoint(_make_messages())[-1]["content"][-1]["cache_control"]
    assert backend_ctl == stream_ctl
