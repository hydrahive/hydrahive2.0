"""num_ctx richtet sich nach freiem VRAM statt nach einem festen 32k-Deckel.

Gemessen auf tills Workstation (RTX 5060 Ti, 16 GiB): gemma4:latest (8B,
Q4_K_M) laeuft auch mit num_ctx=131072 zu 100 % auf der GPU und belegt dabei
nur 7,96 GiB. Der KV-Cache wuchs um ~0,5 GiB je 32k Tokens. Der frueher feste
Deckel von 32768 verschenkte damit das Vierfache an nutzbarem Kontext.
"""
from __future__ import annotations

import pytest

from hydrahive.llm._config import (
    OLLAMA_NUM_CTX_CAP,
    OLLAMA_NUM_CTX_DEFAULT,
    OLLAMA_NUM_CTX_MAX,
    num_ctx_for_ollama,
)
from hydrahive.llm.ollama_fit import free_vram_gib


# --- Fallback-Verhalten ohne VRAM-Information --------------------------------

def test_without_vram_info_falls_back_to_conservative_cap():
    assert num_ctx_for_ollama(131_072) == OLLAMA_NUM_CTX_CAP


def test_unknown_window_returns_default():
    assert num_ctx_for_ollama(None) == OLLAMA_NUM_CTX_DEFAULT
    assert num_ctx_for_ollama(0) == OLLAMA_NUM_CTX_DEFAULT


def test_small_window_is_never_inflated():
    assert num_ctx_for_ollama(8_192, free_vram_gib=14.0) == 8_192


# --- VRAM-abhaengiger Deckel -------------------------------------------------

def test_large_vram_unlocks_full_window():
    """Der eigentliche Fix: 14 GiB frei -> volles 131k-Fenster statt 32k."""
    assert num_ctx_for_ollama(131_072, free_vram_gib=14.0) == 131_072


def test_more_vram_never_shrinks_the_window():
    small = num_ctx_for_ollama(131_072, free_vram_gib=6.0)
    large = num_ctx_for_ollama(131_072, free_vram_gib=14.0)
    assert large >= small > OLLAMA_NUM_CTX_DEFAULT


def test_tight_vram_stays_conservative():
    """4 GiB frei: nach Headroom bleiben 2 GiB -> deutlich unter dem Vollfenster."""
    assert num_ctx_for_ollama(131_072, free_vram_gib=4.0) < 65_536


def test_no_usable_vram_falls_back_to_default_not_zero():
    assert num_ctx_for_ollama(131_072, free_vram_gib=1.0) >= OLLAMA_NUM_CTX_DEFAULT


def test_result_is_aligned_to_8k_steps():
    """Ollama laedt bei jedem geaenderten num_ctx neu — keine wackelnden Werte."""
    for vram in (5.5, 7.3, 9.1, 11.7):
        assert num_ctx_for_ollama(131_072, free_vram_gib=vram) % 8_192 == 0


def test_never_exceeds_hard_maximum():
    assert num_ctx_for_ollama(1_000_000, free_vram_gib=80.0) == OLLAMA_NUM_CTX_MAX


# --- free_vram_gib: llmfit-system-Block auswerten -----------------------------

def test_free_vram_prefers_available_over_total():
    assert free_vram_gib({"gpu_available_gb": 14.3, "gpu_vram_gb": 16.0}) == 14.3


def test_free_vram_falls_back_to_total():
    assert free_vram_gib({"gpu_vram_gb": 16.0}) == 16.0


@pytest.mark.parametrize("system", [None, {}, {"gpu_vram_gb": None}, {"gpu_vram_gb": 0}, "nope"])
def test_free_vram_unknown_returns_none(system):
    assert free_vram_gib(system) is None
