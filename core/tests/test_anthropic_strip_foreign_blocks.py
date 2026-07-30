"""Provider-fremde Blocks dürfen nicht an Anthropic/MiniMax gehen.

Regression: Wechselte eine Session vom Codex-Provider auf Claude, gingen
``codex_reasoning``-Blocks aus der History ungefiltert mit und Anthropic
lehnte JEDEN weiteren Turn mit HTTP 400 ab ("Input tag 'codex_reasoning'
… does not match any of the expected tags"). Betraf reale Sessions —
Fehler in errors_log am 20.07., 24.07., 26.07. und 30.07.2026.
"""
from __future__ import annotations

from hydrahive.runner._anthropic_payload import (
    build_anthropic_kwargs,
    build_minimax_kwargs,
)
from hydrahive.runner._anthropic_sanitize import strip_foreign_blocks

_CODEX = {"type": "codex_reasoning", "encrypted_content": "opaque", "model": "openai-codex/gpt-5.6-sol"}


def _types(messages: list[dict]) -> list[str]:
    return [b.get("type") for m in messages for b in m["content"] if isinstance(b, dict)]


def test_codex_reasoning_wird_entfernt():
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [_CODEX, {"type": "text", "text": "antwort"}]},
    ]
    out = strip_foreign_blocks(msgs)
    assert "codex_reasoning" not in _types(out)
    # Der legitime Text-Block bleibt erhalten
    assert {"type": "text", "text": "antwort"} in out[1]["content"]


def test_erlaubte_bloecke_bleiben_unveraendert():
    msgs = [
        {"role": "assistant", "content": [
            {"type": "text", "text": "t"},
            {"type": "thinking", "thinking": "…", "signature": "s"},
            {"type": "tool_use", "id": "1", "name": "n", "input": {}},
        ]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "1", "content": "ok"}]},
    ]
    assert strip_foreign_blocks(msgs) == msgs


def test_leer_gewordene_message_wird_weggelassen():
    """Realer DB-Fall: Assistant-Turn, der NUR aus codex_reasoning besteht.

    Naiv gefiltert bliebe content=[] übrig — das lehnt Anthropic ebenfalls
    mit 400 ab. Die Message muss deshalb ganz verschwinden.
    """
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [_CODEX]},
        {"role": "user", "content": [{"type": "text", "text": "weiter"}]},
    ]
    out = strip_foreign_blocks(msgs)
    assert len(out) == 2
    assert all(m["content"] for m in out), "keine Message darf leeren content haben"
    assert [m["role"] for m in out] == ["user", "user"]


def test_string_content_bleibt_unangetastet():
    msgs = [{"role": "user", "content": "alte API-Form"}]
    assert strip_foreign_blocks(msgs) == msgs


def test_vorher_schon_leere_message_bleibt():
    """Kein stiller Verhaltenswechsel für bereits leere Messages."""
    msgs = [{"role": "user", "content": []}]
    assert strip_foreign_blocks(msgs) == msgs


def test_build_anthropic_kwargs_sendet_keine_fremden_bloecke():
    """End-to-End: der 400er darf gar nicht erst entstehen können."""
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [_CODEX, {"type": "text", "text": "a"}]},
        {"role": "user", "content": [{"type": "text", "text": "und jetzt claude"}]},
    ]
    _client, kwargs = build_anthropic_kwargs(
        key="sk-plain", model="claude-opus-5", system_prompt="SYS",
        volatile_system=None, summary_system=None, cache_ttl="1h",
        messages=msgs, tools=[], temperature=1.0, max_tokens=100,
        reasoning_effort=None,
    )
    assert "codex_reasoning" not in _types(kwargs["messages"])


def test_build_minimax_kwargs_sendet_keine_fremden_bloecke():
    """MiniMax spricht dasselbe Format — gleiche Filterung nötig."""
    msgs = [
        {"role": "assistant", "content": [_CODEX, {"type": "text", "text": "a"}]},
    ]
    _client, kwargs = build_minimax_kwargs(
        api_key="k", model="MiniMax-M2", system_prompt="SYS",
        volatile_system=None, summary_system=None,
        messages=msgs, tools=[], temperature=1.0, max_tokens=100,
        reasoning_effort=None,
    )
    assert "codex_reasoning" not in _types(kwargs["messages"])


def test_cache_breakpoint_landet_auf_erlaubtem_block():
    """Der Breakpoint darf nicht auf einem Block sitzen, der entfernt wird."""
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "a"}, _CODEX]},
    ]
    _client, kwargs = build_anthropic_kwargs(
        key="sk-plain", model="claude-opus-5", system_prompt="SYS",
        volatile_system=None, summary_system=None, cache_ttl="5m",
        messages=msgs, tools=[], temperature=1.0, max_tokens=100,
        reasoning_effort=None,
    )
    last_block = kwargs["messages"][-1]["content"][-1]
    assert last_block["type"] == "text"
    assert "cache_control" in last_block
