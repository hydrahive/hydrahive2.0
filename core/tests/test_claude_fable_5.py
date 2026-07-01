"""Claude Fable 5 (Release 2026-06-09) ist in allen LLM-Registern eingetragen.

Prüft, dass das neue Anthropic-Top-Coding-Modell überall bekannt ist:
Katalog (auswählbar), Metadata (1M Context, tool_use), Pricing ($10/$50),
Effort-Param-Support (Mythos-Klasse nutzt output_config.effort wie Sonnet 5).
"""
from __future__ import annotations

MODEL = "claude-fable-5"


def test_in_static_catalog():
    from hydrahive.llm._catalog_data import STATIC_MODELS
    assert MODEL in STATIC_MODELS["anthropic"]


def test_metadata_present():
    from hydrahive.llm._catalog_data import METADATA
    meta = METADATA[MODEL]
    assert meta["context_window"] == 1_000_000
    assert meta["tool_use"] is True
    assert meta["family"] == "anthropic"


def test_pricing_present():
    from hydrahive.llm._pricing import lookup
    p = lookup("anthropic", MODEL)
    assert p is not None
    # $10 input / $50 output in Micro-Cents ($ × 0.1).
    assert p.input == 1.0
    assert p.output == 5.0
    assert p.cache_read == 0.1
    assert p.cache_creation == 1.25


def test_supports_effort_param():
    from hydrahive.llm._anthropic import _uses_effort_param
    assert _uses_effort_param(MODEL) is True
    # auch mit Provider-Prefix (falls je über LiteLLM geroutet):
    assert _uses_effort_param("anthropic/" + MODEL) is True


def test_catalog_enrich_marks_effort():
    from hydrahive.llm.catalog import _enrich
    assert _enrich("anthropic", {"id": MODEL})["supports_effort"] is True
