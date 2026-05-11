"""Tests für _with_cache_breakpoint — TTL muss 1h sein (Token-Audit-Fix).

Vorher: hardcoded {"type": "ephemeral"} ohne ttl → Anthropic-Default 5m
→ alle 5 Minuten Cache-Reset, ~€1+ pro Re-Create bei großen Sessions.
Aus der "analyse claude code"-Session: 4 Cache-Resets in 9 Minuten = ~€5.
"""
from __future__ import annotations

from hydrahive.runner._llm_bridge_backends import (
    _with_cache_breakpoint as backend_breakpoint,
)
from hydrahive.runner._stream_providers import (
    _with_cache_breakpoint as stream_breakpoint,
)


def _make_messages() -> list[dict]:
    return [
        {"role": "user", "content": [{"type": "text", "text": "Hi"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "user", "content": [{"type": "text", "text": "Next"}]},
    ]


def test_backend_default_ttl_ist_1h():
    msgs = backend_breakpoint(_make_messages())
    # messages[-2] (assistant) hat cache_control mit ttl=1h
    cache_ctl = msgs[-2]["content"][-1].get("cache_control")
    assert cache_ctl is not None
    assert cache_ctl["type"] == "ephemeral"
    assert cache_ctl.get("ttl") == "1h"


def test_stream_default_ttl_ist_1h():
    msgs = stream_breakpoint(_make_messages())
    cache_ctl = msgs[-2]["content"][-1].get("cache_control")
    assert cache_ctl is not None
    assert cache_ctl["type"] == "ephemeral"
    assert cache_ctl.get("ttl") == "1h"


def test_explicit_5m_setzt_kein_ttl_feld():
    """5m ist Anthropic-Default — wir setzen explizit kein 'ttl' Feld."""
    msgs = backend_breakpoint(_make_messages(), ttl="5m")
    cache_ctl = msgs[-2]["content"][-1].get("cache_control")
    assert cache_ctl["type"] == "ephemeral"
    assert "ttl" not in cache_ctl


def test_kurze_messages_ohne_breakpoint():
    # < 2 Messages → unverändert zurück
    one = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
    out = backend_breakpoint(one)
    assert out == one
    assert "cache_control" not in out[0]["content"][0]


def test_ttl_durchgereicht_an_alle_provider():
    """Sicherheits-Check dass beide Bridge-Module die gleiche Default-TTL haben."""
    backend_ctl = backend_breakpoint(_make_messages())[-2]["content"][-1]["cache_control"]
    stream_ctl = stream_breakpoint(_make_messages())[-2]["content"][-1]["cache_control"]
    assert backend_ctl == stream_ctl
