"""build_anthropic_kwargs / build_minimax_kwargs single-source die Payload-
Assembly für Stream + Non-Stream (Issue #200, Teil 3).

Diese Tests nageln die Cache-Ordering fest — die delikate Stelle, die laut
Projekt-Memory schon einmal den Prompt-Cache gebrochen hat.
"""
from __future__ import annotations

from hydrahive.runner._anthropic_payload import (
    build_anthropic_kwargs,
    build_minimax_kwargs,
    strip_minimax_cache_control,
)


_MESSAGES = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
_TOOLS = [{"name": "a", "input_schema": {}}, {"name": "b", "input_schema": {}}]


def test_anthropic_kwargs_cache_ordering():
    _client, kwargs = build_anthropic_kwargs(
        key="sk-plain", model="claude-x", system_prompt="SYS",
        volatile_system="VOL", summary_system="SUM", cache_ttl="5m",
        messages=_MESSAGES, tools=_TOOLS, temperature=1.0, max_tokens=100,
        reasoning_effort=None,
    )
    sys_blocks = kwargs["system"]
    # Reihenfolge: system_prompt (cache) → summary (cache) → volatile (NO cache, zuletzt)
    assert [b["text"] for b in sys_blocks] == ["SYS", "SUM", "VOL"]
    assert "cache_control" in sys_blocks[0]
    assert "cache_control" in sys_blocks[1]
    assert "cache_control" not in sys_blocks[2], "volatile darf den Cache nicht brechen"
    # Breakpoint: letzter Content-Block der letzten Message ist markiert
    assert "cache_control" in kwargs["messages"][-1]["content"][-1]
    # cached_tools: nur das LETZTE Tool trägt cache_control
    assert "cache_control" not in kwargs["tools"][0]
    assert "cache_control" in kwargs["tools"][-1]


def test_anthropic_kwargs_oauth_prepends_identity():
    _client, kwargs = build_anthropic_kwargs(
        key="sk-ant-oat-xxx", model="claude-x", system_prompt="SYS",
        volatile_system=None, summary_system=None, cache_ttl="5m",
        messages=_MESSAGES, tools=[], temperature=1.0, max_tokens=100,
        reasoning_effort=None,
    )
    # OAuth-Identity-Block kommt VOR system_prompt
    assert kwargs["system"][0]["text"] != "SYS"
    assert any(b["text"] == "SYS" for b in kwargs["system"])


def test_minimax_kwargs_single_string_system_no_cache():
    msgs = [{"role": "user", "content": [{"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}}]}]
    tools = [{"name": "a", "input_schema": {}, "cache_control": {"type": "ephemeral"}}]
    _client, kwargs = build_minimax_kwargs(
        api_key="mk", model="MiniMax-x", system_prompt="A",
        volatile_system="C", summary_system="B",
        messages=msgs, tools=tools, temperature=1.0, max_tokens=100,
        reasoning_effort=None,
    )
    assert kwargs["system"] == "A\n\nB\n\nC"  # einzelner String, Reihenfolge sys+summary+volatile
    assert isinstance(kwargs["system"], str)
    # cache_control wurde aus messages + tools entfernt (MiniMax → sonst HTTP 500)
    assert "cache_control" not in kwargs["messages"][0]["content"][0]
    assert "cache_control" not in kwargs["tools"][0]


def test_strip_minimax_cache_control():
    msgs = [{"role": "user", "content": [{"type": "text", "text": "x", "cache_control": {}}]}]
    tools = [{"name": "t", "cache_control": {}}]
    clean_msgs, clean_tools = strip_minimax_cache_control(msgs, tools)
    assert "cache_control" not in clean_msgs[0]["content"][0]
    assert "cache_control" not in clean_tools[0]
