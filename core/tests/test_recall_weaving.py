"""Task 5 — Recall A: render_cards_block + compose-Injektion in den Stable-Prompt.
Pure (kein PG/LLM): compose ist sync, render_cards_block rein."""
from __future__ import annotations

from pathlib import Path

from hydrahive.runner.system_prompt import compose, render_cards_block


def test_render_cards_block_basic():
    cards = [
        {"gist": "baute Card-Store", "valence": "good", "topics": ["cards", "pg"]},
        {"gist": "", "valence": "bad", "topics": []},  # leerer gist → skip
    ]
    out = render_cards_block(cards)
    assert "baute Card-Store" in out and "[good]" in out and "cards, pg" in out
    assert "Erinnerungen" in out
    assert out.count("- [") == 1  # gistlose Card nicht enthalten


def test_render_cards_block_empty():
    assert render_cards_block([]) == ""
    assert render_cards_block([{"gist": "", "valence": "neutral"}]) == ""


def test_compose_injects_recall_into_stable_not_volatile():
    stable, volatile, _ = compose(
        "BASE-PROMPT",
        extra_system=None, workspace=Path("/tmp/ws"), summary=None, skills=None,
        longterm_memory=False, tool_schemas=[], allowed_tools=[],
        recall_cards=[{"gist": "frühere Session X", "valence": "good", "topics": ["x"]}],
    )
    assert "frühere Session X" in stable          # im STABLE-Block (cache-fähig)
    assert "frühere Session X" not in volatile     # NICHT im volatile (sonst Cache-Bruch)
    assert "Erinnerungen" in stable


def test_compose_without_recall_cards_has_no_block():
    stable, _, _ = compose(
        "BASE", extra_system=None, workspace=Path("/tmp"), summary=None, skills=None,
        longterm_memory=False, tool_schemas=[], allowed_tools=[], recall_cards=None,
    )
    assert "Erinnerungen (automatisch" not in stable
