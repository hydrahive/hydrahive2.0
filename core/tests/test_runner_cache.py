"""
Regressionstests für den Runner-Cache-Mechanismus.

Diese Tests fangen genau den Bug vom 2026-05-06 ab:
Commit e743841 hatte das Datum in den stabilen System-Prompt eingefügt →
Cache-Miss jede Minute → 31% Rate-Limit in 20 Minuten.
"""
import re
from pathlib import Path

from hydrahive.runner.system_prompt import compose as build_system_prompts


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
#
# Diese Tests prüfen direkt die echte build_system_prompts-Funktion,
# nicht eine nachgebaute Helper-Logik. Damit ist ausgeschlossen dass
# der Test grün bleibt obwohl der echte Code abweicht.
# ---------------------------------------------------------------------------

DATUM_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}")
UHRZEIT_REGEX = re.compile(r"\d{2}:\d{2}")


def _build(base: str = "Du bist ein Agent.", *, summary: str | None = None, extra: str | None = None):
    return build_system_prompts(
        base, extra_system=extra, workspace=Path("/var/lib/hydrahive2/workspaces/test"),
        summary=summary, skills=None, longterm_memory=False, tool_schemas=[], allowed_tools=[],
    )


def test_stable_enthaelt_kein_datum():
    """Datum im stable_system = Cache-Miss jede Minute — der Bug vom 2026-05-06."""
    stable, _, _ = _build()
    assert not DATUM_REGEX.search(stable), (
        "stable_system enthält ein Datum! Das verhindert Prompt-Caching."
    )


def test_stable_enthaelt_keine_uhrzeit():
    stable, _, _ = _build()
    assert not UHRZEIT_REGEX.search(stable), (
        "stable_system enthält eine Uhrzeit! Das verhindert Prompt-Caching."
    )


def test_volatile_enthaelt_datum():
    _, volatile, _ = _build()
    assert DATUM_REGEX.search(volatile), "volatile_system muss das aktuelle Datum enthalten."


def test_volatile_enthaelt_keine_uhrzeit():
    """Issue #141: Uhrzeit im volatile_system bricht den Cache jede Minute."""
    _, volatile, _ = _build()
    assert not UHRZEIT_REGEX.search(volatile), (
        "volatile_system enthält eine Uhrzeit! Anthropic prüft den ganzen "
        "System-Block — Minuten-Wechsel resetten den Cache (Issue #141)."
    )


def test_summary_als_eigener_system_block():
    """summary kommt aus build_system_prompts als separater 3. Rückgabewert,
    nicht in volatile_system eingewoben — sonst entweicht der Cache-Hit
    durch sich ändernde Zusammenfassungen."""
    _, volatile, summary_system = _build(summary="Wir haben über X gesprochen.")
    assert summary_system is not None
    assert "Bisherige Zusammenfassung" in summary_system
    assert "Wir haben über X gesprochen." in summary_system
    assert "Bisherige Zusammenfassung" not in volatile


def test_summary_none_wenn_kein_summary():
    _, _, summary_system = _build()
    assert summary_system is None


def test_stable_unveraendert_ohne_extra_system():
    base = "Mein fester System-Prompt ohne Datum."
    stable, _, _ = _build(base)
    # base muss im stable enthalten sein — Reihenfolge (z.B. mit Workspace
    # darunter, Stufe B #135) wird nicht getestet, nur die Anwesenheit.
    assert base in stable


def test_extra_system_wird_vorangestellt():
    """extra_system (z.B. Sprach-Hinweis von Voice-API) sitzt vor base."""
    stable, _, _ = _build("BASE_PROMPT", extra="Antworte auf Deutsch.")
    assert stable.startswith("Antworte auf Deutsch.")
    assert "BASE_PROMPT" in stable


# ---------------------------------------------------------------------------
# 4. Workspace im stable (Issue #135) — Cache-Stabilität
# ---------------------------------------------------------------------------


def test_workspace_im_stable_system():
    """Issue #135: Workspace gehört in den stable-Block (pro Agent konstant),
    nicht in volatile. Sonst bricht der Cache bei tool_config-Override."""
    stable, _, _ = _build()
    assert "/var/lib/hydrahive2/workspaces/test" in stable
    assert "Workspace:" in stable


def test_workspace_NICHT_im_volatile_system():
    """Regression-Guard: wenn jemand Workspace zurück in volatile schiebt,
    soll dieser Test scheitern."""
    _, volatile, _ = _build()
    assert "Workspace:" not in volatile, (
        "Workspace darf nicht in volatile_system — gehört in stable (#135)."
    )


def test_workspace_unter_base_prompt_in_stable():
    """Ordnung im stable: [extra_system\\n\\n]base\\n\\nWorkspace.
    Workspace sitzt am Ende, nach dem base-Prompt."""
    stable, _, _ = _build("BASE_HIER")
    base_idx = stable.index("BASE_HIER")
    workspace_idx = stable.index("Workspace:")
    assert workspace_idx > base_idx, "Workspace muss NACH base_system_prompt stehen."
