"""SSOT für die Compaction-Schwelle: TokenMeter-Anzeige == echter Trigger.

Der Chat-Header-Balken (`/tokens` → compact_threshold) und der Runner-Trigger
(`should_compact`) müssen sich aus DERSELBEN Reserve ableiten, sonst zeigt der
Balken einen anderen %-Wert als den, bei dem wirklich compactet wird.
"""
from __future__ import annotations

from hydrahive.compaction import (
    DEFAULT_RESERVE_TOKENS,
    compact_threshold_tokens,
    effective_reserve_tokens,
    should_compact,
)
from hydrahive.compaction.tokens import context_window_for

HAIKU = "claude-haiku-4-5"
WINDOW = 200_000  # context_window_for(HAIKU)


def test_threshold_pct_75_feuert_bei_75_prozent():
    # 200k Window, 75% → effektiv 50k Reserve → Schwelle bei 150k
    assert compact_threshold_tokens(HAIKU, threshold_pct=75, reserve_tokens=16_384) == 150_000


def test_threshold_pct_100_nutzt_reine_reserve():
    # 100% = Früh-Compaction aus → Reserve bleibt 16384 → Window - 16384
    assert compact_threshold_tokens(HAIKU, threshold_pct=100, reserve_tokens=16_384) == WINDOW - 16_384


def test_grosse_reserve_schlaegt_pct_headroom():
    # Reserve größer als die pct-Headroom (50k) → Reserve gewinnt
    assert compact_threshold_tokens(HAIKU, threshold_pct=75, reserve_tokens=60_000) == WINDOW - 60_000


def test_none_reserve_faellt_auf_default_zurueck():
    # Kein Reserve gesetzt → should_compact-Default greift
    assert (
        compact_threshold_tokens(HAIKU, threshold_pct=100, reserve_tokens=None)
        == WINDOW - DEFAULT_RESERVE_TOKENS
    )


def test_invariante_meter_schwelle_gleich_trigger_reserve():
    """Die vom Balken gezeigte 100%-Marke == der Punkt, an dem should_compact umklappt.

    Beide leiten sich aus `window - reserve` ab; entscheidend ist, dass es
    DIESELBE reserve ist. Das pinnt den SSOT-Vertrag fest.
    """
    for pct in (50, 75, 100):
        for reserve in (16_384, 40_000):
            eff = effective_reserve_tokens(HAIKU, threshold_pct=pct, reserve_tokens=reserve)
            threshold = compact_threshold_tokens(HAIKU, threshold_pct=pct, reserve_tokens=reserve)
            assert threshold == context_window_for(HAIKU) - eff


def test_behavioral_balken_100_faellt_mit_trigger_zusammen():
    """Sobald used die Schwelle übersteigt, triggert should_compact UND der
    Balken steht auf 100% — nicht vorher, nicht nachher."""
    pct, reserve = 75, 16_384
    threshold = compact_threshold_tokens(HAIKU, threshold_pct=pct, reserve_tokens=reserve)
    eff = effective_reserve_tokens(HAIKU, threshold_pct=pct, reserve_tokens=reserve)

    # Nachricht knapp ÜBER der Schwelle → muss triggern, Balken auf 100%
    over = [_msg(threshold + 5_000)]
    assert should_compact(over, HAIKU, reserve_tokens=eff) is True
    assert min(100, _meter_pct(over, threshold)) == 100

    # Nachricht klar UNTER der Schwelle → darf nicht triggern, Balken < 100
    under = [_msg(threshold - 30_000)]
    assert should_compact(under, HAIKU, reserve_tokens=eff) is False
    assert _meter_pct(under, threshold) < 100


def _msg(tokens: int):
    from types import SimpleNamespace

    return SimpleNamespace(token_count=tokens, content=None)


def _meter_pct(messages: list, threshold: int) -> float:
    from hydrahive.compaction import total_tokens

    return total_tokens(messages) / threshold * 100
