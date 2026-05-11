"""Tests für _with_cache_breakpoint — TTL-Verhalten.

Geschichte: 1h-TTL wurde getestet (commit b8ca92a + 0a648b3) und verworfen.
Anthropic-Cache wird auch innerhalb der 5min server-side evictet (LRU bei
Storage-Druck), 1h-cache_creation kostet aber 2× — netto teurer.
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


def test_backend_default_ttl_ist_5m():
    msgs = backend_breakpoint(_make_messages())
    cache_ctl = msgs[-2]["content"][-1].get("cache_control")
    assert cache_ctl is not None
    assert cache_ctl["type"] == "ephemeral"
    # 5m ist Anthropic-Default — kein ttl-Feld
    assert "ttl" not in cache_ctl


def test_stream_default_ttl_ist_5m():
    msgs = stream_breakpoint(_make_messages())
    cache_ctl = msgs[-2]["content"][-1].get("cache_control")
    assert cache_ctl is not None
    assert cache_ctl["type"] == "ephemeral"
    assert "ttl" not in cache_ctl


def test_explicit_1h_setzt_ttl_feld():
    """Per-Call kann immer noch 1h gesetzt werden — aber nur wenn nötig
    (z.B. für Tools-Cache der wirklich lange stabil ist)."""
    msgs = backend_breakpoint(_make_messages(), ttl="1h")
    cache_ctl = msgs[-2]["content"][-1].get("cache_control")
    assert cache_ctl["type"] == "ephemeral"
    assert cache_ctl["ttl"] == "1h"


def test_kurze_messages_ohne_breakpoint():
    one = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
    out = backend_breakpoint(one)
    assert out == one
    assert "cache_control" not in out[0]["content"][0]


def test_ttl_durchgereicht_an_alle_provider():
    backend_ctl = backend_breakpoint(_make_messages())[-2]["content"][-1]["cache_control"]
    stream_ctl = stream_breakpoint(_make_messages())[-2]["content"][-1]["cache_control"]
    assert backend_ctl == stream_ctl
