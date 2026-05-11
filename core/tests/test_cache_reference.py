"""Tests für _add_cache_reference_to_tool_results (Task 2 der Cache-Diet).

Quelle: claude-code-source-code/src/services/api/claude.ts:3164-3207
"""
from __future__ import annotations

from hydrahive.runner._llm_bridge_backends import (
    _add_cache_reference_to_tool_results as backend_add_ref,
    _with_cache_breakpoint as backend_breakpoint,
)
from hydrahive.runner._stream_providers import (
    _add_cache_reference_to_tool_results as stream_add_ref,
    _with_cache_breakpoint as stream_breakpoint,
)


def _typical_history() -> list[dict]:
    """Realistische History: user → asst(tool_use) → user(tool_result) → asst(tool_use) → user(tool_result + new prompt)"""
    return [
        {"role": "user", "content": [
            {"type": "text", "text": "Erste Aufgabe"},
        ]},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_aaa", "name": "shell_exec", "input": {"cmd": "ls"}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_aaa", "content": "file1\nfile2"},
        ]},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_bbb", "name": "file_read", "input": {"path": "file1"}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_bbb", "content": "Inhalt von file1"},
            {"type": "text", "text": "Weitermachen"},
        ]},
    ]


def test_cache_reference_auf_alle_alten_tool_results():
    msgs = backend_breakpoint(_typical_history())
    msgs = backend_add_ref(msgs)

    # messages[2] hat das erste tool_result (toolu_aaa) — sollte cache_reference bekommen
    tr1 = msgs[2]["content"][0]
    assert tr1["type"] == "tool_result"
    assert tr1["cache_reference"] == "toolu_aaa"

    # messages[4] = letzte message mit cache_control marker (von _with_cache_breakpoint)
    # → das tool_result dort darf KEIN cache_reference haben (strictly before)
    tr2 = msgs[4]["content"][0]
    assert tr2["type"] == "tool_result"
    assert "cache_reference" not in tr2


def test_keine_cache_reference_ohne_cache_control():
    """Wenn keine cache_control marker existiert, kein cache_reference setzen."""
    raw = _typical_history()  # ohne _with_cache_breakpoint
    out = backend_add_ref(raw)
    for msg in out:
        if not isinstance(msg.get("content"), list):
            continue
        for block in msg["content"]:
            assert "cache_reference" not in block


def test_assistant_messages_unangetastet():
    """cache_reference nur auf user-message tool_results — assistant-tool_use bleibt."""
    msgs = backend_breakpoint(_typical_history())
    msgs = backend_add_ref(msgs)
    # messages[1] und messages[3] sind assistant-Messages mit tool_use blocks
    for idx in (1, 3):
        for block in msgs[idx]["content"]:
            assert "cache_reference" not in block


def test_stream_provider_identisches_verhalten():
    backend_out = backend_add_ref(backend_breakpoint(_typical_history()))
    stream_out = stream_add_ref(stream_breakpoint(_typical_history()))
    assert backend_out == stream_out


def test_tool_result_ohne_tool_use_id_wird_ignoriert():
    """Defensive: malformed tool_result ohne tool_use_id wird nicht annotiert."""
    msgs = [
        {"role": "user", "content": [
            {"type": "tool_result", "content": "broken"},  # kein tool_use_id
        ]},
        {"role": "assistant", "content": [{"type": "text", "text": "x"}]},
        {"role": "user", "content": [{"type": "text", "text": "now"}]},
    ]
    out = backend_add_ref(backend_breakpoint(msgs))
    tr = out[0]["content"][0]
    assert "cache_reference" not in tr


def test_idempotent():
    """Zweimal anwenden = einmal anwenden."""
    once = backend_add_ref(backend_breakpoint(_typical_history()))
    twice = backend_add_ref(once)
    assert once == twice
