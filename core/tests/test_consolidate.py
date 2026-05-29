"""Task 4 (Card-Writer) — pure Logik + gemockter consolidate_session-Flow.

Ohne PG/LLM: die echten DB/LLM/Embed-Ops sind gemockt (Till verifiziert die
Runtime nach Deploy). Hier wird die Verdichtungs-/Tag-Logik + die korrekte
Card-Zusammensetzung geprüft.
"""
from __future__ import annotations

import asyncio


# --- pure: parse_card_response ------------------------------------------------

def test_parse_card_valid():
    from hydrahive.cards._consolidate_prompts import parse_card_response
    out = parse_card_response('{"gist":"baute X","valence":"good","salience":"high","topics":["projx","ci"]}')
    assert out == {"gist": "baute X", "valence": "good", "salience": "high", "topics": ["projx", "ci"]}


def test_parse_card_strips_code_fence():
    from hydrahive.cards._consolidate_prompts import parse_card_response
    out = parse_card_response('```json\n{"gist":"g","valence":"bad","salience":"low","topics":[]}\n```')
    assert out["gist"] == "g" and out["valence"] == "bad"


def test_parse_card_validates_enums_and_caps_topics():
    from hydrahive.cards._consolidate_prompts import parse_card_response
    out = parse_card_response('{"gist":"g","valence":"meh","salience":"mega","topics":["a","b","c","d","e","f","g"]}')
    assert out["valence"] == "neutral"   # ungültig → neutral
    assert out["salience"] == "low"      # ungültig → low
    assert len(out["topics"]) == 6       # gecappt


def test_parse_card_garbage_is_fallback():
    from hydrahive.cards._consolidate_prompts import parse_card_response
    out = parse_card_response("kein json")
    assert out == {"gist": "", "valence": "neutral", "salience": "low", "topics": []}


# --- pure: format_session_text ------------------------------------------------

def test_format_empty():
    from hydrahive.cards._consolidate_prompts import format_session_text
    assert format_session_text([]) == "(no events)"


def test_format_basic():
    from hydrahive.cards._consolidate_prompts import format_session_text
    out = format_session_text([
        {"event_type": "user_input", "text": "hallo"},
        {"event_type": "tool_result", "tool_name": "Bash", "tool_output": "ok"},
    ])
    assert "[user_input] hallo" in out and "[tool_result:Bash] ok" in out


def test_format_truncates_large_session():
    from hydrahive.cards._consolidate_prompts import format_session_text
    events = [{"event_type": "user_input", "text": "x" * 100} for _ in range(200)]
    out = format_session_text(events, char_budget=500)
    assert "chars elided" in out
    assert len(out) < 700  # budget + Marker, nicht der volle ~20k-Text


# --- gemockter Flow: consolidate_session --------------------------------------

def test_consolidate_session_builds_card(monkeypatch):
    import hydrahive.cards.consolidate as c

    async def fake_detail(session_id):
        return {
            "session": {"agent_id": "a-uuid", "agent_name": "joshua22",
                        "username": "joshua22", "started_at": "2026-05-29T10:00:00Z"},
            "events": [{"event_type": "user_input", "text": "hi"},
                       {"event_type": "tool_result", "tool_name": "Bash", "tool_output": "ok"}],
        }

    async def fake_counts(session_id):
        return {"tool_result": 10, "assistant_text": 2}  # → observed

    captured = {}

    async def fake_upsert(card, embedding=None):
        captured["card"] = card
        captured["embedding"] = embedding

    async def fake_llm(**kw):
        text = '{"gist":"did X","valence":"good","salience":"high","topics":["projx"]}'
        return ([{"type": "text", "text": text}], "", {})

    monkeypatch.setattr(c, "get_session_detail", fake_detail)
    monkeypatch.setattr(c, "event_type_counts", fake_counts)
    monkeypatch.setattr(c, "upsert_card", fake_upsert)
    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {"embed_model": ""})

    card = asyncio.run(c.consolidate_session("s1", "test-model"))

    assert card is not None
    assert card.card_id == "card:s1" and card.session_id == "s1"
    assert card.gist == "did X" and card.valence == "good" and card.salience == "high"
    assert card.groundedness == "observed"          # 10 tool_result vs 2 assistant_text
    assert card.topics == ["projx"]
    assert card.agent_id == "a-uuid" and card.agent_name == "joshua22"
    assert card.username == "joshua22" and card.created_at == "2026-05-29T10:00:00Z"
    assert card.source == {"session_id": "s1", "event_count": 2}
    assert card.consolidation_model == "test-model"
    assert captured["card"] is card and captured["embedding"] is None  # embed_model leer → kein Embedding


def test_consolidate_session_missing_returns_none(monkeypatch):
    import hydrahive.cards.consolidate as c

    async def fake_detail(session_id):
        return None

    monkeypatch.setattr(c, "get_session_detail", fake_detail)
    assert asyncio.run(c.consolidate_session("nope", "m")) is None


def test_scheduler_module_imports():
    # faengt Syntaxfehler im Scheduler-Takt (consolidate_recent-Einhaengung)
    import hydrahive.zahnfee.scheduler  # noqa: F401


def test_consolidate_recent_contract_for_scheduler():
    # der zahnfee-Scheduler ruft consolidate_recent(lookback_hours, model) beim Tages-Tick
    import inspect

    from hydrahive.cards.consolidate import consolidate_recent
    assert inspect.iscoroutinefunction(consolidate_recent)
    p = inspect.signature(consolidate_recent).parameters
    assert "lookback_hours" in p and "model" in p


def test_parse_card_robust_extraction():
    # NIM-Varianz: JSON in Prosa / mit Trailing / gefenced / Klammern-in-Strings
    from hydrahive.cards._consolidate_prompts import parse_card_response
    prose = 'Here is the card:\n{"gist":"g","valence":"good","salience":"high","topics":["a"]}\nDone.'
    assert parse_card_response(prose) == {"gist": "g", "valence": "good", "salience": "high", "topics": ["a"]}
    fenced = '```json\n{"gist":"f","valence":"bad","salience":"low","topics":[]}\n```'
    assert parse_card_response(fenced)["gist"] == "f"
    nested = '{"gist":"has {brace} in str","valence":"neutral","salience":"low","topics":[]}'
    assert parse_card_response(nested)["gist"] == "has {brace} in str"
