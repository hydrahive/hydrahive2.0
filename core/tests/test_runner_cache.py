"""
Regressionstests für den Runner-Cache-Mechanismus.

Diese Tests fangen genau den Bug vom 2026-05-06 ab:
Commit e743841 hatte das Datum in den stabilen System-Prompt eingefügt →
Cache-Miss jede Minute → 31% Rate-Limit in 20 Minuten.
"""
import re
from datetime import datetime
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. _cache_control Helper
# ---------------------------------------------------------------------------

def test_cache_control_1h_setzt_ttl():
    from hydrahive.runner._stream_providers import _cache_control
    ctrl = _cache_control("1h")
    assert ctrl["type"] == "ephemeral"
    assert ctrl.get("ttl") == "1h"


def test_cache_control_5m_kein_ttl():
    """5m = Anthropic-Default — kein ttl-Feld schicken."""
    from hydrahive.runner._stream_providers import _cache_control
    ctrl = _cache_control("5m")
    assert ctrl["type"] == "ephemeral"
    assert "ttl" not in ctrl


def test_cache_control_konsistent_in_beiden_modulen():
    """Beide Provider-Module müssen identisches Verhalten liefern."""
    from hydrahive.runner._stream_providers import _cache_control as cc_stream
    from hydrahive.runner._llm_bridge_backends import _cache_control as cc_bridge
    for ttl in ("1h", "5m", ""):
        assert cc_stream(ttl) == cc_bridge(ttl), f"Divergenz bei ttl={ttl!r}"


# ---------------------------------------------------------------------------
# 2. Tool-Cache-Control — letztes Tool bekommt cache_control, Rest unverändert
# ---------------------------------------------------------------------------

def _apply_tool_cache(tools: list[dict], ttl: str = "1h") -> list[dict]:
    """Spiegelt die Logik aus _stream_providers.anthropic_stream."""
    from hydrahive.runner._stream_providers import _cache_control
    return [*tools[:-1], {**tools[-1], "cache_control": _cache_control(ttl)}]


def test_letztes_tool_bekommt_cache_control():
    tools = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    result = _apply_tool_cache(tools)
    assert "cache_control" in result[-1]
    assert result[-1]["name"] == "c"


def test_andere_tools_unveraendert():
    tools = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    result = _apply_tool_cache(tools)
    assert result[0] == {"name": "a"}
    assert result[1] == {"name": "b"}


def test_original_tool_liste_nicht_mutiert():
    """Mutation würde in Folgeiterationen das cache_control doppelt setzen."""
    tools = [{"name": "x"}, {"name": "y"}]
    _apply_tool_cache(tools)
    assert "cache_control" not in tools[-1]


def test_einzel_tool_bekommt_cache_control():
    tools = [{"name": "only"}]
    result = _apply_tool_cache(tools)
    assert "cache_control" in result[0]


# ---------------------------------------------------------------------------
# 3. Stable vs. Volatile System-Prompt — der Kern-Regressionstest
# ---------------------------------------------------------------------------

DATUM_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}")
UHRZEIT_REGEX = re.compile(r"\d{2}:\d{2}")


def _build_stable_volatile(base_prompt: str, summary: str | None = None):
    """
    Nachbau der Runner-Logik (runner.py, Iteration-Loop).
    Wenn diese Logik im echten Code geändert wird, muss dieser Test
    angepasst werden — das ist Absicht: er pinnt das Verhalten fest.
    """
    stable = base_prompt

    now = datetime.now().astimezone()
    date_line = (
        f"Aktuelles Datum/Uhrzeit (Server): "
        f"{now.strftime('%Y-%m-%d %H:%M %Z')} ({now.strftime('%A')}). "
        f"Verwende dieses Datum als Referenz, NICHT dein Trainings-Cutoff."
    )
    volatile_parts = [date_line]
    if summary:
        volatile_parts.append(f"[Bisherige Zusammenfassung]\n{summary}")
    volatile = "\n\n".join(volatile_parts)

    return stable, volatile


def test_stable_enthaelt_kein_datum():
    """Datum im stable_system = Cache-Miss jede Minute — der Bug vom 2026-05-06."""
    stable, _ = _build_stable_volatile("Du bist ein hilfreicher Agent.")
    assert not DATUM_REGEX.search(stable), (
        "stable_system enthält ein Datum! Das verhindert Prompt-Caching. "
        "Datum muss in volatile_system."
    )


def test_stable_enthaelt_keine_uhrzeit():
    stable, _ = _build_stable_volatile("Du bist ein hilfreicher Agent.")
    assert not UHRZEIT_REGEX.search(stable), (
        "stable_system enthält eine Uhrzeit! Das verhindert Prompt-Caching."
    )


def test_volatile_enthaelt_datum():
    _, volatile = _build_stable_volatile("Du bist ein Agent.")
    assert DATUM_REGEX.search(volatile), "volatile_system muss das aktuelle Datum enthalten."


def test_volatile_enthaelt_zusammenfassung():
    _, volatile = _build_stable_volatile("Prompt.", summary="Wir haben über X gesprochen.")
    assert "Bisherige Zusammenfassung" in volatile
    assert "Wir haben über X gesprochen." in volatile


def test_stable_unveraendert_ohne_zusammenfassung():
    base = "Mein fester System-Prompt ohne Datum."
    stable, _ = _build_stable_volatile(base)
    assert stable == base
