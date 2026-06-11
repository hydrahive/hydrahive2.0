"""Turn-Netz skaliert mit dem Context-Window.

Der feste 1000-Nachrichten-Deckel würgte tool-lastige Sessions auf 1M-Modellen
(Opus 4.7/4.8) bei ~37% des Fensters ab — lange vor der Token-Linie. Der Deckel
skaliert jetzt mit dem Window, sodass auf großen Modellen die Token-Schwelle
regiert und das Turn-Netz nur echter Runaway-Schutz bleibt. Floor bleibt 1000
(Loop-Schutz: nach Compaction werden ~20k Tokens behalten — der Deckel darf nie
unter die Zahl behaltener Nachrichten fallen).
"""
from __future__ import annotations

from types import SimpleNamespace

from hydrahive.compaction import default_max_turns, should_compact

OPUS = "claude-opus-4-8"
SONNET = "claude-sonnet-4-6"


def _msg(tokens: int):
    return SimpleNamespace(token_count=tokens, content=None)


def test_default_max_turns_scales_with_window():
    assert default_max_turns(OPUS) == 5000          # 1M / 200
    assert default_max_turns(SONNET) == 1000        # 200k / 200 (Alt-Default erhalten)
    assert default_max_turns("claude-haiku-4-5") == 1000


def test_small_window_keeps_floor():
    # 32k-Modell: window/200=160, aber Floor 1000 (Token-Trigger feuert eh früher).
    assert default_max_turns("qwen2.5-coder") == 1000


def test_tool_heavy_opus_session_below_token_line_not_compacted():
    # Tills Fall: ~1200 kleine Nachrichten, zusammen ~372k Tokens, 75%-Linie = 750k.
    # Alt (fix 1000): Turn-Netz feuerte. Neu (5000): weder Token- noch Turn-Trigger.
    msgs = [_msg(310) for _ in range(1200)]   # ~372k Tokens, 1200 Nachrichten
    eff_reserve = 250_000                     # 75% von 1M → Schwelle 750k
    assert should_compact(msgs, OPUS, reserve_tokens=eff_reserve) is False


def test_runaway_turn_net_still_fires_on_opus():
    # 5001 winzige Nachrichten → Turn-Netz greift weiterhin als Runaway-Schutz.
    msgs = [_msg(1) for _ in range(5001)]
    assert should_compact(msgs, OPUS, reserve_tokens=250_000) is True


def test_token_line_still_governs_on_opus():
    # Wenige, aber riesige Nachrichten über der Token-Linie → Token-Trigger feuert.
    msgs = [_msg(800_000)]
    assert should_compact(msgs, OPUS, reserve_tokens=250_000) is True


def test_explicit_max_turns_overrides_scaled_default():
    msgs = [_msg(10) for _ in range(150)]
    assert should_compact(msgs, OPUS, reserve_tokens=250_000, max_turns=100) is True
    assert should_compact(msgs, OPUS, reserve_tokens=250_000, max_turns=500) is False


# --- Validierung des user-gesetzten Werts (Loop-Schutz) ----------------------

def test_user_set_compact_max_turns_below_floor_rejected():
    """Ein zu niedriger Wert würde den Loop-sicheren Floor umgehen → 400."""
    import pytest

    from hydrahive.agents._validation import AgentValidationError, normalize_compact_changes

    for bad in (5, 100, 999):
        with pytest.raises(AgentValidationError):
            normalize_compact_changes({"compact_max_turns": bad})


def test_user_set_compact_max_turns_valid_passes_and_casts():
    from hydrahive.agents._validation import normalize_compact_changes

    changes = {"compact_max_turns": "8000"}
    normalize_compact_changes(changes)
    assert changes["compact_max_turns"] == 8000


def test_compact_max_turns_none_clears_to_auto():
    # None/leer → entfernt → normalize() backfillt None = window-skalierter Default.
    from hydrahive.agents._validation import normalize_compact_changes

    changes = {"compact_max_turns": None}
    normalize_compact_changes(changes)
    assert "compact_max_turns" not in changes
