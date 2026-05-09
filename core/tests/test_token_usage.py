"""Tests für _token_usage — Token-Extraction-Helper für non-Streaming-Pfad."""
from __future__ import annotations

from types import SimpleNamespace

from hydrahive.runner._token_usage import (
    empty_usage,
    usage_dict,
    usage_from_litellm,
)


def test_empty_usage_alle_null():
    u = empty_usage()
    assert u == {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }


def test_usage_dict_none_returns_empty():
    assert usage_dict(None) == empty_usage()


def test_usage_dict_voller_anthropic_usage():
    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=200,
        cache_read_input_tokens=300,
    )
    result = usage_dict(usage)
    assert result == {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_creation_tokens": 200,
        "cache_read_tokens": 300,
    }


def test_usage_dict_fehlende_felder_default_0():
    usage = SimpleNamespace(input_tokens=42)
    result = usage_dict(usage)
    assert result["input_tokens"] == 42
    assert result["output_tokens"] == 0
    assert result["cache_creation_tokens"] == 0
    assert result["cache_read_tokens"] == 0


def test_usage_dict_none_werte_werden_zu_null():
    """Anthropic kann explizit None statt 0 schicken — wir mappen auf 0."""
    usage = SimpleNamespace(
        input_tokens=10, output_tokens=None,
        cache_creation_input_tokens=None, cache_read_input_tokens=None,
    )
    result = usage_dict(usage)
    assert result["output_tokens"] == 0
    assert result["cache_creation_tokens"] == 0
    assert result["cache_read_tokens"] == 0


def test_usage_from_litellm_openai_format():
    """LiteLLM liefert OpenAI-Format: prompt_tokens + completion_tokens."""
    resp = SimpleNamespace(usage=SimpleNamespace(
        prompt_tokens=200,
        completion_tokens=80,
    ))
    result = usage_from_litellm(resp)
    assert result["input_tokens"] == 200
    assert result["output_tokens"] == 80
    assert result["cache_creation_tokens"] == 0
    assert result["cache_read_tokens"] == 0


def test_usage_from_litellm_kein_usage_returns_empty():
    resp = SimpleNamespace(usage=None)
    assert usage_from_litellm(resp) == empty_usage()


def test_usage_from_litellm_mit_cache_tokens():
    """LiteLLM kann cache-Felder durchreichen wenn der Provider sie liefert."""
    resp = SimpleNamespace(usage=SimpleNamespace(
        prompt_tokens=100, completion_tokens=20,
        cache_creation_input_tokens=50, cache_read_input_tokens=70,
    ))
    result = usage_from_litellm(resp)
    assert result == {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_creation_tokens": 50,
        "cache_read_tokens": 70,
    }
