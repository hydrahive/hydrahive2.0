"""Tests für Compaction — pure Functions, kein DB-Setup.

Deckt tokens.py (Estimates + context_window_for), cut_point.py
(Cut-Point-Suche mit tool_result-Boundaries), compactor.py
(should_compact/total_tokens).
"""
from __future__ import annotations

from hydrahive.compaction.compactor import (
    DEFAULT_RESERVE_TOKENS,
    should_compact,
    total_tokens,
)
from hydrahive.compaction.cut_point import find_cut_point
from hydrahive.compaction.tokens import (
    context_window_for,
    estimate_dense_text,
    estimate_message,
    estimate_message_content,
    estimate_text,
)
from hydrahive.db.messages import Message


def _msg(role: str, content, msg_id: str = "m1", token_count: int | None = None) -> Message:
    return Message(id=msg_id, session_id="s1", role=role, content=content,
                   created_at="2026-05-09T00:00:00Z",
                   token_count=token_count, metadata={})


# --- tokens.py -----------------------------------------------------------

def test_estimate_text_proportional_zur_laenge():
    assert estimate_text("a" * 100) > estimate_text("a" * 10)


def test_estimate_text_leerer_string_min_1():
    assert estimate_text("") == 1


def test_estimate_dense_text_groesser_als_estimate_text():
    """Dense Estimate ist konservativer = höhere Token-Counts."""
    text = "x" * 1000
    assert estimate_dense_text(text) > estimate_text(text)


def test_estimate_message_nutzt_cache_wenn_vorhanden():
    m = _msg("user", "ein langer ungenutzter content " * 100, token_count=42)
    assert estimate_message(m) == 42


def test_estimate_message_fallback_auf_content_wenn_kein_cache():
    m = _msg("user", "hi", token_count=None)
    assert estimate_message(m) == estimate_text("hi")


def test_estimate_message_content_string():
    assert estimate_message_content("hello") == estimate_text("hello")


def test_estimate_message_content_none_ist_0():
    assert estimate_message_content(None) == 0


def test_estimate_message_content_block_list_summiert():
    blocks = [
        {"type": "text", "text": "hi"},
        {"type": "tool_use", "id": "tu1", "name": "x", "input": {}},
    ]
    assert estimate_message_content(blocks) > estimate_text("hi")


# --- context_window_for --------------------------------------------------

def test_context_window_opus_4_7_ist_1m():
    assert context_window_for("claude-opus-4-7") == 1_000_000


def test_context_window_sonnet_4_6_ist_200k():
    assert context_window_for("claude-sonnet-4-6") == 200_000


def test_context_window_gpt4o_ist_128k():
    assert context_window_for("gpt-4o") == 128_000


def test_context_window_gemini_ist_1m():
    assert context_window_for("gemini-2.0-pro") == 1_000_000


def test_context_window_minimax_ist_256k():
    assert context_window_for("minimax-m2") == 256_000


def test_context_window_qwen25_coder_ist_32k():
    assert context_window_for("qwen2.5-coder-32b") == 32_000


def test_context_window_qwen3_ist_262144():
    assert context_window_for("qwen3-coder-30b") == 262_144


def test_context_window_unknown_model_default_32k():
    assert context_window_for("völlig-unbekannt-xyz") == 32_000


def test_context_window_case_insensitive():
    assert context_window_for("CLAUDE-OPUS-4-7") == 1_000_000


# --- compactor: should_compact + total_tokens ----------------------------

def test_total_tokens_summiert_alle_messages():
    msgs = [_msg("user", "a", token_count=10), _msg("assistant", "b", token_count=20)]
    assert total_tokens(msgs) == 30


def test_total_tokens_leere_liste_ist_0():
    assert total_tokens([]) == 0


def test_should_compact_unter_limit_false():
    """gpt-4o = 128k Window, Reserve 16k → Cap 112k. 50k Tokens → kein Compact."""
    msgs = [_msg("user", "x", token_count=50_000)]
    assert should_compact(msgs, "gpt-4o") is False


def test_should_compact_ueber_limit_true():
    """gpt-4o = 128k - 16k reserve = 112k cap. 200k Tokens → Compact."""
    msgs = [_msg("user", "x", token_count=200_000)]
    assert should_compact(msgs, "gpt-4o") is True


def test_should_compact_custom_reserve():
    """200k Window, 50k Tokens, Reserve 100k → Cap 100k → 50k unter Cap."""
    msgs = [_msg("user", "x", token_count=50_000)]
    assert should_compact(msgs, "claude-sonnet-4-6", reserve_tokens=100_000) is False
    # Reserve 180k → Cap 20k → 50k über Cap
    assert should_compact(msgs, "claude-sonnet-4-6", reserve_tokens=180_000) is True


def test_should_compact_default_reserve_ist_16k():
    """Ohne reserve_tokens-Argument muss DEFAULT_RESERVE_TOKENS=16384 greifen."""
    # opus-4-7 hat 1M Window. 990k tokens → 990k > 1M-16k=984k → True
    msgs = [_msg("user", "x", token_count=990_000)]
    assert should_compact(msgs, "claude-opus-4-7") is True
    # 980k tokens → 980k < 984k → False
    msgs = [_msg("user", "x", token_count=980_000)]
    assert should_compact(msgs, "claude-opus-4-7") is False


# --- cut_point.find_cut_point --------------------------------------------

def test_find_cut_point_leere_liste():
    assert find_cut_point([], 1000).kept_from_index == 0


def test_find_cut_point_alles_passt_in_budget():
    msgs = [_msg("user", "a", token_count=10), _msg("assistant", "b", token_count=10)]
    cp = find_cut_point(msgs, 1000)
    assert cp.kept_from_index == 0


def test_find_cut_point_einfacher_schnitt():
    """4 Messages je 100 Tokens. Budget 250 → letzten 2 behalten (≈200t)."""
    msgs = [
        _msg("user", "a", "m1", token_count=100),
        _msg("assistant", "b", "m2", token_count=100),
        _msg("user", "c", "m3", token_count=100),
        _msg("assistant", "d", "m4", token_count=100),
    ]
    cp = find_cut_point(msgs, 250)
    # Walk-back nimmt m4(100)+m3(100)=200 ≤ 250, m2 dazu → 300 > 250 → cut bei i+1=2
    assert cp.kept_from_index == 2


def test_find_cut_point_skippt_tool_results_als_first_kept():
    """tool_result darf nie der erste gekippte Block werden — der zugehörige
    tool_use bleibt sonst orphaned. Cut wandert weiter vor."""
    msgs = [
        _msg("user", "a", "m1", token_count=50),
        _msg("assistant", [{"type": "tool_use", "id": "tu1", "name": "x", "input": {}}],
             "m2", token_count=50),
        _msg("user", [{"type": "tool_result", "tool_use_id": "tu1", "content": "ok"}],
             "m3", token_count=50),
        _msg("assistant", "after", "m4", token_count=50),
    ]
    # Budget so wählen dass naive Cut bei m3 (tool_result) landen würde
    cp = find_cut_point(msgs, 70)
    # Cut darf NICHT bei einem reinen tool_result-Message sein
    if cp.kept_from_index < len(msgs):
        first_kept = msgs[cp.kept_from_index]
        is_tool_result_only = (
            first_kept.role == "user"
            and isinstance(first_kept.content, list)
            and all(b.get("type") == "tool_result" for b in first_kept.content if isinstance(b, dict))
        )
        assert not is_tool_result_only


def test_find_cut_point_split_turn_wenn_ein_turn_groesser_budget():
    """Ein einziger Turn > Budget → split-turn-Modus."""
    msgs = [
        _msg("user", "huge prompt", "m1", token_count=10_000),
        _msg("assistant", "huge reply", "m2", token_count=10_000),
    ]
    cp = find_cut_point(msgs, 5_000)
    # Single turn, beide zusammen 20k > 5k Budget → split-turn-Pfad
    assert cp.is_split_turn or cp.kept_from_index == len(msgs)
