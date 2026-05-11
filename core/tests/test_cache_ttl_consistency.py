"""Tests für konsistente Cache-TTL pro Request (Task 3 der Cache-Diet).

Quelle: claude-code-source-code/src/services/api/claude.ts:358-414 (getCacheControl)
+ bootstrap/state.ts:251 ("cache TTL is ~5min")

Alle cache_control eines Requests nutzen denselben TTL-Wert. HH2 hatte
vorher Mix: system="1h", summary="5m" hardcoded, tools="1h", messages
variabel. Mix → Cache-Inkonsistenz.
"""
from __future__ import annotations

from hydrahive.agents._defaults import DEFAULT_CACHE_TTL


def test_default_cache_ttl_ist_5m():
    """Claude Code-Default = 5min, Anthropic-Default = 5min ohne extended-cache-ttl."""
    assert DEFAULT_CACHE_TTL == "5m"


def test_normalize_setzt_5m_default():
    from hydrahive.agents._config_utils import normalize
    cfg = {"id": "a1", "name": "test"}
    out = normalize(cfg)
    assert out["cache_ttl"] == "5m"


def test_keine_hardcoded_5m_mehr_in_bridge():
    """Hardcoded _cache_control('5m') Strings dürfen nicht mehr existieren —
    alle cache_control nutzen den param cache_ttl."""
    import inspect

    from hydrahive.runner import _llm_bridge_backends, _stream_providers
    for mod in (_llm_bridge_backends, _stream_providers):
        src = inspect.getsource(mod)
        assert '_cache_control("5m")' not in src, (
            f"Hardcoded _cache_control('5m') in {mod.__name__} — muss "
            f"_cache_control(cache_ttl) sein"
        )


def test_kein_hardcoded_1h_default_mehr():
    """Default-Wert in Bridge-Funktionen soll '5m' sein, nicht '1h'."""
    import inspect

    from hydrahive.runner import _llm_bridge_backends, _stream_providers
    for mod in (_llm_bridge_backends, _stream_providers):
        src = inspect.getsource(mod)
        # cache_ttl: str = "1h" darf nicht mehr da sein
        assert 'cache_ttl: str = "1h"' not in src
        # cache_ttl: str = "5m" muss da sein
        assert 'cache_ttl: str = "5m"' in src
