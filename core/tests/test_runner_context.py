"""Tests für die pure Functions im Runner — context.py + dispatcher.py.

Kein DB-Setup, kein LLM-Mock — nur Daten rein, Daten raus.
"""
from __future__ import annotations

from hydrahive.db.messages import Message
from hydrahive.runner.context import (
    _sanitize_block,
    extract_tool_uses,
    has_visible_content,
    heal_orphan_tool_uses,
    merge_text_blocks,
    to_anthropic_messages,
)
from hydrahive.runner.dispatcher import to_tool_result_block
from hydrahive.tools.base import ToolResult


def _msg(role: str, content, msg_id: str = "m1") -> Message:
    return Message(id=msg_id, session_id="s1", role=role, content=content,
                   created_at="2026-05-09T00:00:00Z", token_count=None, metadata={})


# --- to_tool_result_block ------------------------------------------------

def test_tool_result_block_success():
    block = to_tool_result_block("tu1", ToolResult.ok("hi"))
    assert block["type"] == "tool_result"
    assert block["tool_use_id"] == "tu1"
    assert block["content"] == "hi"
    assert block["is_error"] is False


def test_tool_result_block_fail():
    block = to_tool_result_block("tu1", ToolResult.fail("boom"))
    assert block["is_error"] is True
    assert "boom" in block["content"]


def test_tool_result_block_setzt_tool_name():
    block = to_tool_result_block("tu1", ToolResult.ok("x"), tool_name="shell_exec")
    assert block["tool_name"] == "shell_exec"


def test_tool_result_block_ohne_tool_name_kein_feld():
    block = to_tool_result_block("tu1", ToolResult.ok("x"))
    assert "tool_name" not in block


def test_tool_result_block_max_chars_0_keine_truncation():
    long = "x" * 1000
    block = to_tool_result_block("tu1", ToolResult.ok(long), max_chars=0)
    assert block["content"] == long


def test_tool_result_block_max_chars_groesser_als_content():
    block = to_tool_result_block("tu1", ToolResult.ok("hi"), max_chars=1000)
    assert block["content"] == "hi"


def test_tool_result_block_max_chars_kuerzer_truncated():
    long = "x" * 100
    block = to_tool_result_block("tu1", ToolResult.ok(long), max_chars=20)
    assert block["content"].startswith("x" * 20)
    assert "abgeschnitten" in block["content"]
    assert "tool_result_max_chars=20" in block["content"]


# --- _sanitize_block -----------------------------------------------------

def test_sanitize_text_block_nur_type_und_text():
    block = {"type": "text", "text": "hi", "extra": "drop"}
    assert _sanitize_block(block) == {"type": "text", "text": "hi"}


def test_sanitize_tool_result_filtert_extra_felder():
    block = {"type": "tool_result", "tool_use_id": "tu1", "content": "ok",
             "is_error": False, "tool_name": "shell_exec", "media": [{"kind": "image"}]}
    out = _sanitize_block(block)
    assert "tool_name" not in out
    assert "media" not in out
    assert out["tool_use_id"] == "tu1"


def test_sanitize_thinking_returns_none():
    assert _sanitize_block({"type": "thinking", "thinking": "secret", "signature": "abc"}) is None


def test_sanitize_unknown_type_durchgelassen():
    block = {"type": "custom_xyz", "field": "value"}
    assert _sanitize_block(block) == block


def test_sanitize_non_dict_durchgelassen():
    assert _sanitize_block("plain text") == "plain text"


# --- to_anthropic_messages -----------------------------------------------

def test_to_anthropic_messages_filtert_system():
    history = [_msg("system", "rules"), _msg("user", "hi")]
    out = to_anthropic_messages(history)
    assert len(out) == 1
    assert out[0]["role"] == "user"


def test_to_anthropic_messages_tool_role_wird_user():
    history = [_msg("tool", "result")]
    out = to_anthropic_messages(history)
    assert out[0]["role"] == "user"


def test_to_anthropic_messages_filtert_leere_content():
    history = [_msg("user", ""), _msg("user", "real"), _msg("assistant", [])]
    out = to_anthropic_messages(history)
    assert len(out) == 1
    assert out[0]["content"] == "real"


def test_to_anthropic_messages_strippt_thinking_blocks():
    history = [_msg("assistant", [
        {"type": "thinking", "thinking": "secret", "signature": "abc"},
        {"type": "text", "text": "hello"},
    ])]
    out = to_anthropic_messages(history)
    assert out[0]["content"] == [{"type": "text", "text": "hello"}]


# --- extract_tool_uses + merge_text_blocks -------------------------------

def test_extract_tool_uses_filtert_nur_tool_use():
    blocks = [
        {"type": "text", "text": "hi"},
        {"type": "tool_use", "id": "tu1", "name": "shell_exec", "input": {}},
        {"type": "text", "text": "more"},
    ]
    out = extract_tool_uses(blocks)
    assert len(out) == 1
    assert out[0]["id"] == "tu1"


def test_merge_text_blocks_join_mit_newline():
    blocks = [
        {"type": "text", "text": "first"},
        {"type": "tool_use", "id": "tu1"},
        {"type": "text", "text": "second"},
    ]
    assert merge_text_blocks(blocks) == "first\nsecond"


def test_merge_text_blocks_ueberspringt_leere_strings():
    blocks = [
        {"type": "text", "text": "a"},
        {"type": "text", "text": ""},
        {"type": "text", "text": "b"},
    ]
    assert merge_text_blocks(blocks) == "a\nb"


# --- heal_orphan_tool_uses -----------------------------------------------

def test_heal_synthetisches_result_wenn_nichts_folgt():
    """tool_use ohne darauffolgendes tool_result → synthetic injected."""
    history = [
        _msg("assistant", [{"type": "tool_use", "id": "tu1", "name": "x", "input": {}}], msg_id="m1"),
    ]
    out = heal_orphan_tool_uses(history)
    assert len(out) == 2
    assert out[1].role == "user"
    assert any(b.get("tool_use_id") == "tu1" for b in out[1].content)
    assert out[1].content[0]["is_error"] is True


def test_heal_kein_eingriff_wenn_result_da_ist():
    history = [
        _msg("assistant", [{"type": "tool_use", "id": "tu1", "name": "x", "input": {}}], msg_id="m1"),
        _msg("user", [{"type": "tool_result", "tool_use_id": "tu1", "content": "ok"}], msg_id="m2"),
    ]
    out = heal_orphan_tool_uses(history)
    assert len(out) == 2
    # Inhalte unverändert (kein synthetischer Block dazu)
    assert len(out[1].content) == 1


def test_heal_einer_von_zwei_tool_uses_fehlt():
    """Bestehende tool_results bleiben, fehlender wird ergänzt."""
    history = [
        _msg("assistant", [
            {"type": "tool_use", "id": "tu1", "name": "x", "input": {}},
            {"type": "tool_use", "id": "tu2", "name": "x", "input": {}},
        ], msg_id="m1"),
        _msg("user", [
            {"type": "tool_result", "tool_use_id": "tu1", "content": "ok"},
        ], msg_id="m2"),
    ]
    out = heal_orphan_tool_uses(history)
    user_msg = out[1]
    ids = {b["tool_use_id"] for b in user_msg.content if b.get("type") == "tool_result"}
    assert ids == {"tu1", "tu2"}


def test_heal_strippt_orphaned_tool_result():
    """tool_result ohne passenden tool_use → wird entfernt."""
    history = [
        _msg("assistant", [{"type": "tool_use", "id": "tu1", "name": "x", "input": {}}], msg_id="m1"),
        _msg("user", [
            {"type": "tool_result", "tool_use_id": "tu1", "content": "ok"},
            {"type": "tool_result", "tool_use_id": "ORPHAN", "content": "stale"},
        ], msg_id="m2"),
    ]
    out = heal_orphan_tool_uses(history)
    user_blocks = out[1].content
    ids = {b.get("tool_use_id") for b in user_blocks}
    assert "ORPHAN" not in ids
    assert "tu1" in ids


def test_heal_dedupliziert_doppelte_tool_results():
    """Gleiche tool_use_id zwei Mal → nur ein Block bleibt."""
    history = [
        _msg("assistant", [{"type": "tool_use", "id": "tu1", "name": "x", "input": {}}], msg_id="m1"),
        _msg("user", [
            {"type": "tool_result", "tool_use_id": "tu1", "content": "first"},
            {"type": "tool_result", "tool_use_id": "tu1", "content": "duplicate"},
        ], msg_id="m2"),
    ]
    out = heal_orphan_tool_uses(history)
    results = [b for b in out[1].content if b.get("type") == "tool_result"]
    assert len(results) == 1
    assert results[0]["content"] == "first"


def test_has_visible_content_true_for_text():
    assert has_visible_content([{"type": "text", "text": "Hallo"}]) is True


def test_has_visible_content_true_for_tool_use():
    assert has_visible_content([{"type": "tool_use", "id": "t1", "name": "x", "input": {}}]) is True


def test_has_visible_content_false_for_empty():
    assert has_visible_content([]) is False


def test_has_visible_content_false_for_whitespace_only_text():
    assert has_visible_content([{"type": "text", "text": "   \n  "}]) is False


def test_has_visible_content_false_for_reasoning_only():
    # Nur reasoning/thinking ohne Text/Tool → gilt als leerer Turn.
    blocks = [
        {"type": "codex_reasoning", "encrypted_content": "enc", "model": "openai-codex/gpt-5.6-sol"},
        {"type": "thinking", "thinking": "hmm", "signature": "s"},
    ]
    assert has_visible_content(blocks) is False


def test_has_visible_content_true_when_text_alongside_reasoning():
    blocks = [
        {"type": "codex_reasoning", "encrypted_content": "enc", "model": "m"},
        {"type": "text", "text": "Antwort"},
    ]
    assert has_visible_content(blocks) is True
