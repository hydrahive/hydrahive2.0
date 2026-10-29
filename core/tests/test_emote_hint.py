"""Buddy-System-Prompt bekommt zur Laufzeit den Hydra-Emote-Hinweis angehängt —
aber nur der Buddy (is_buddy), nicht normale Agenten.
"""
from __future__ import annotations


def test_buddy_bekommt_hint_angehaengt():
    from hydrahive.runner._emote_hint import with_emote_hint

    out = with_emote_hint("BASIS-PROMPT", is_buddy=True)

    assert out.startswith("BASIS-PROMPT")
    assert out != "BASIS-PROMPT"
    assert ":hydra-" in out
    # ein paar echte Namen müssen drin sein
    assert "thumbsup" in out
    assert "pirate" in out


def test_normaler_agent_bleibt_unveraendert():
    from hydrahive.runner._emote_hint import with_emote_hint

    assert with_emote_hint("BASIS-PROMPT", is_buddy=False) == "BASIS-PROMPT"


def test_buddy_kennt_genau_die_emotes_aus_dem_frontend():
    """Task 0dda5420: Die Liste für den Buddy darf nicht hinter dem Emote-Ordner zurückbleiben."""
    from pathlib import Path

    from hydrahive.runner._emote_hint import EMOTE_NAMES

    ordner = Path(__file__).resolve().parents[2] / "frontend" / "public" / "illustrations" / "emoticons"
    dateien = sorted(p.stem.removeprefix("hydra-") for p in ordner.glob("hydra-*.png"))
    assert dateien, "Emote-Ordner nicht gefunden"
    assert sorted(EMOTE_NAMES) == dateien
    assert len(EMOTE_NAMES) == len(set(EMOTE_NAMES))


def test_hint_enthaelt_anwendungs_anweisung():
    from hydrahive.runner._emote_hint import HYDRA_EMOTE_HINT

    # erklärt das Format + mahnt sparsamen Einsatz
    assert ":hydra-NAME:" in HYDRA_EMOTE_HINT
    assert "sparsam" in HYDRA_EMOTE_HINT.lower()
