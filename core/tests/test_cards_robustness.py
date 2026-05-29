"""Robustheit der Card-Konsolidierung gegen LLM-Output-Varianz.

Fixtures sind echte Haiku-Rohantworten (raw.log 2026-05-29), die in der ersten
Implementation lautlos leere Cards erzeugten:
- Mode 2: echoed Hook-JSON VOR der echten Card → Extraktion griff das falsche {…}.
"""
from __future__ import annotations

from hydrahive.cards._consolidate_prompts import parse_card_response

# Mode 2 (raw.log, Session 2ecf6ba0): echoed [system_stop_hook_summary] {…} VOR
# der korrekten Card. Die echte Card hat den "gist"-Key.
MODE2 = (
    'Läuft jetzt?\n[system_stop_hook_summary] {"parentUuid": "a8c8", '
    '"hookInfos": [{"command": "x"}], "lastPrompt": "nein"}\n```\n\n```json\n'
    '{"gist": "Analyzed ATLAS_OS & UI-TARS; debugged bubbletea TUI raw-mode.", '
    '"valence": "good", "salience": "high", "topics": ["ATLAS_OS", "UI-TARS"]}\n```'
)


def test_extraction_skips_echoed_object_and_finds_card():
    out = parse_card_response(MODE2)
    assert out["gist"].startswith("Analyzed ATLAS_OS")
    assert out["valence"] == "good" and out["salience"] == "high"
    assert "ATLAS_OS" in out["topics"]


def test_card_user_message_frames_transcript():
    from hydrahive.cards._consolidate_prompts import card_user_message
    msg = card_user_message([{"event_type": "user_input", "text": "hi"}])
    assert "BEGIN SESSION TRANSCRIPT" in msg and "END SESSION TRANSCRIPT" in msg
    assert "[user_input] hi" in msg


def test_claude_prefill_reconstructs_json(monkeypatch):
    import asyncio

    import hydrahive.cards.consolidate as c

    seen = {}

    async def fake_llm(**kw):
        seen["messages"] = kw["messages"]
        # Anthropic gibt die Fortsetzung OHNE das vorangestellte "{" zurück
        cont = '"gist":"did X","valence":"good","salience":"high","topics":["projx"]}'
        return ([{"type": "text", "text": cont}], "", {})

    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    tags = asyncio.run(c._llm_tags(
        [{"event_type": "user_input", "text": "hi"}], "claude-haiku-4-5"))

    assert tags["gist"] == "did X" and tags["valence"] == "good"
    assert seen["messages"][-1] == {"role": "assistant", "content": "{"}  # Prefill gesetzt


def test_no_prefill_for_non_claude(monkeypatch):
    import asyncio

    import hydrahive.cards.consolidate as c

    seen = {}

    async def fake_llm(**kw):
        seen["messages"] = kw["messages"]
        return ([{"type": "text", "text": '{"gist":"y","valence":"neutral","salience":"low","topics":[]}'}], "", {})

    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    tags = asyncio.run(c._llm_tags([{"event_type": "user_input", "text": "hi"}], "nvidia_nim/qwen"))

    assert tags["gist"] == "y"
    assert all(m["role"] != "assistant" for m in seen["messages"])  # kein Prefill
