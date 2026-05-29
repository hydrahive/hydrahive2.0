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


def test_retry_then_success(monkeypatch):
    import asyncio

    import hydrahive.cards.consolidate as c
    calls = {"n": 0}

    async def fake_detail(sid):
        return {"session": {}, "events": [{"event_type": "user_input", "text": "hi"}]}

    async def fake_counts(sid):
        return {"tool_result": 0, "assistant_text": 1}

    captured = {}

    async def fake_upsert(card, embedding=None):
        captured["card"] = card

    async def fake_llm(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return ([{"type": "text", "text": "Alles klar!"}], "", {})  # Mode-1-Prosa
        return ([{"type": "text", "text": '{"gist":"ok","valence":"good","salience":"low","topics":[]}'}], "", {})

    monkeypatch.setattr(c, "get_session_detail", fake_detail)
    monkeypatch.setattr(c, "event_type_counts", fake_counts)
    monkeypatch.setattr(c, "upsert_card", fake_upsert)
    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {"embed_model": ""})

    card = asyncio.run(c.consolidate_session("s1", "x-model"))
    assert calls["n"] == 2 and card is not None and card.gist == "ok"


def test_persistent_empty_returns_none_and_no_upsert(monkeypatch):
    import asyncio

    import hydrahive.cards.consolidate as c
    upserts = {"n": 0}

    async def fake_detail(sid):
        return {"session": {}, "events": [{"event_type": "user_input", "text": "hi"}]}

    async def fake_upsert(card, embedding=None):
        upserts["n"] += 1

    async def fake_llm(**kw):
        return ([{"type": "text", "text": "Alles klar, ich antworte nur Prosa."}], "", {})

    monkeypatch.setattr(c, "get_session_detail", fake_detail)
    monkeypatch.setattr(c, "upsert_card", fake_upsert)
    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)

    card = asyncio.run(c.consolidate_session("s1", "x-model"))
    assert card is None and upserts["n"] == 0  # nichts Leeres gespeichert


# --- Review-Findings: Scanner-/Prefill-Robustheit --------------------------------

def test_extraction_recovers_card_after_unbalanced_brace():
    # echoed Content mit unbalanciertem { VOR der Card (z.B. abgeschnittener Code)
    txt = 'echoed: def f() { incomplete...\n{"gist":"real","valence":"good","salience":"high","topics":["x"]}'
    out = parse_card_response(txt)
    assert out["gist"] == "real" and out["valence"] == "good"


def test_prefill_double_brace_recovers():
    # Modell gab trotz Prefill ein eigenes { aus → "{" + text = "{{...}"
    out = parse_card_response("{" + '{"gist":"x","valence":"neutral","salience":"low","topics":[]}')
    assert out["gist"] == "x"


def test_extraction_picks_last_gist_object():
    # echoed Objekt das selbst einen gist-Key trägt, VOR der echten Card → letztes gewinnt
    txt = '{"gist":"WRONG","foo":1}\n{"gist":"RIGHT","valence":"good","salience":"low","topics":[]}'
    out = parse_card_response(txt)
    assert out["gist"] == "RIGHT"


def test_prefill_rejection_falls_back_to_no_prefill(monkeypatch):
    import asyncio

    import hydrahive.cards.consolidate as c
    seen = []

    async def fake_llm(**kw):
        seen.append(kw["messages"])
        if kw["messages"][-1].get("role") == "assistant":  # Prefill-Versuch
            raise RuntimeError("Prefilling assistant messages is not supported for this model")
        return ([{"type": "text", "text": '{"gist":"recovered","valence":"good","salience":"low","topics":[]}'}], "", {})

    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    tags = asyncio.run(c._llm_tags([{"event_type": "user_input", "text": "hi"}], "claude-opus-4-7"))
    assert tags["gist"] == "recovered"
    assert len(seen) == 2  # erst Prefill (abgelehnt), dann ohne
