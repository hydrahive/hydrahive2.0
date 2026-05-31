"""Embed-Registry: OpenRouter-Embedder (bge-m3) muss auswählbar sein.

dim_for_model dimensioniert die pgvector-Spalte (_mirror_ddl), available_for_config
füttert das UI-Dropdown (api/routes/llm). Slug + dim sind gegen OpenRouters
Katalog verifiziert (baai/bge-m3-20251117, 1024-dim).
"""
from __future__ import annotations

from hydrahive.llm import embed

BGE_M3 = "baai/bge-m3-20251117"


def test_bge_m3_dimension_ist_1024():
    assert embed.dim_for_model(BGE_M3) == 1024


def test_bge_m3_key_lookup_geht_auf_openrouter():
    """api_base-Pfad löst den Key über den Provider auf — muss 'openrouter' sein."""
    assert embed._PROVIDER_BY_MODEL[BGE_M3] == "openrouter"


def test_bge_m3_nutzt_openrouter_api_base():
    entry = embed._BY_MODEL[BGE_M3]
    assert entry["api_base"] == "https://openrouter.ai/api/v1"


def test_available_for_config_zeigt_bge_m3_mit_openrouter_key():
    config = {"providers": [{"id": "openrouter", "api_key": "sk-or-v1-test"}]}
    models = embed.available_for_config(config)
    match = [m for m in models if m["model"] == BGE_M3]
    assert match, "bge-m3 fehlt obwohl OpenRouter-Key gesetzt"
    assert match[0]["dim"] == 1024
    assert match[0]["provider"] == "openrouter"


def test_available_for_config_ohne_key_kein_bge_m3():
    config = {"providers": [{"id": "openrouter", "api_key": ""}]}
    models = embed.available_for_config(config)
    assert not any(m["model"] == BGE_M3 for m in models)
