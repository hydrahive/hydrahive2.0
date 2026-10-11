"""Antwortsprache für alle Agenten aus der Buddy-Einstellung (docs/specs/agent-language.md).

Quelle ist `_pref_language` am Buddy des Nutzers, für den der Lauf läuft. de/en → fester Block im stabilen Prompt,
auto → kein Block, kein Buddy oder unbekannter Wert → de.
"""
from __future__ import annotations

import pytest


MODEL = "claude-3-7-sonnet-20250219"


@pytest.fixture
def buddy(client):
    """Buddy-Agent je Nutzer mit Sprach-Einstellung im echten Memory-Speicher."""
    from hydrahive.agents import config as agent_config
    from hydrahive.tools import _memory_store as memory

    made: list[str] = []

    def make(username: str, language: str | None) -> str:
        a = agent_config.create(agent_type="master", name=f"Buddy {username}", llm_model=MODEL,
                                owner=username, created_by=username, temperature=0.7, max_tokens=1000,
                                thinking_budget=0)
        agent_config.update(a["id"], is_buddy=True)
        if language is not None:
            memory.write_key(a["id"], "_pref_language", language)
        made.append(a["id"])
        return a["id"]

    yield make
    for aid in made:
        agent_config.delete(aid)


def test_german_block_for_de(buddy):
    from hydrahive.runner._language_rule import language_for, with_language_rule
    buddy("lang-de", "de")
    assert language_for("lang-de") == "de"
    out = with_language_rule("BASIS", "de")
    assert out.startswith("BASIS\n\n## Sprache\n")
    assert "Antworte immer auf Deutsch" in out
    assert "Zwischensätze vor Werkzeugaufrufen" in out
    assert "Code, Befehle" in out


def test_english_block_for_en(buddy):
    from hydrahive.runner._language_rule import language_for, with_language_rule
    buddy("lang-en", "en")
    assert language_for("lang-en") == "en"
    out = with_language_rule("BASE", "en")
    assert out.startswith("BASE\n\n## Language\n")
    assert "Always respond in English" in out
    assert "Deutsch" not in out


def test_auto_adds_nothing(buddy):
    from hydrahive.runner._language_rule import language_for, with_language_rule
    buddy("lang-auto", "auto")
    assert language_for("lang-auto") == "auto"
    assert with_language_rule("BASIS", "auto") == "BASIS"


@pytest.mark.parametrize("value", [None, "", "fr", "DE", "de; rm -rf /"])
def test_missing_or_unknown_value_means_german(buddy, value):
    from hydrahive.runner._language_rule import language_for
    buddy(f"lang-x{abs(hash(str(value))) % 10000}", value)
    assert language_for(f"lang-x{abs(hash(str(value))) % 10000}") == "de"


def test_user_without_buddy_gets_german(client):
    from hydrahive.runner._language_rule import language_for
    assert language_for("niemand-hat-buddy") == "de"


def test_other_users_buddy_does_not_count(buddy):
    """Die Sprache kommt nur vom Buddy des Nutzers des Laufs – nicht von einem fremden Buddy."""
    from hydrahive.runner._language_rule import language_for
    buddy("lang-anna", "en")
    assert language_for("lang-bernd") == "de"


def test_non_buddy_agent_of_the_user_does_not_count(buddy):
    """Ein normaler Agent mit (irrtümlich) gesetztem _pref_language zählt nicht – nur der Buddy."""
    from hydrahive.agents import config as agent_config
    from hydrahive.runner._language_rule import language_for
    from hydrahive.tools import _memory_store as memory
    a = agent_config.create(agent_type="master", name="Kein Buddy", llm_model=MODEL,
                            owner="lang-carl", created_by="lang-carl", temperature=0.7, max_tokens=1000,
                            thinking_budget=0)
    memory.write_key(a["id"], "_pref_language", "en")
    try:
        assert language_for("lang-carl") == "de"
    finally:
        agent_config.delete(a["id"])


def test_block_is_stable_bytes(buddy):
    """Gleiche Eingabe → byte-gleicher Block (Prompt-Cache)."""
    from hydrahive.runner._language_rule import with_language_rule
    assert with_language_rule("X", "de") == with_language_rule("X", "de")
