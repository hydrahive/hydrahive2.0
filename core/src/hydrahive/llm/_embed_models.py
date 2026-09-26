"""Technische Metadaten und ID-Auflösung für Embedding-Modelle.

Die Tabelle bestimmt nicht die Verfügbarkeit; das übernimmt der Live-Katalog.
"""
from __future__ import annotations

from typing import Any


EMBED_MODELS: dict[str, list[dict[str, Any]]] = {
    "openai": [
        {"model": "text-embedding-3-small", "litellm": "text-embedding-3-small", "dim": 1536},
        {"model": "text-embedding-3-large", "litellm": "text-embedding-3-large", "dim": 3072},
        {"model": "text-embedding-ada-002", "litellm": "text-embedding-ada-002", "dim": 1536},
    ],
    "nvidia": [
        {
            "model": "nvidia/nv-embed-v1",
            "litellm": "openai/nvidia/nv-embed-v1",
            "api_base": "https://integrate.api.nvidia.com/v1",
            "dim": 4096,
        },
        {
            "model": "nvidia/nv-embedqa-e5-v5",
            "litellm": "openai/nvidia/nv-embedqa-e5-v5",
            "api_base": "https://integrate.api.nvidia.com/v1",
            "dim": 1024,
        },
    ],
    "minimax": [
        {
            "model": "minimax/embo-01",
            "litellm": "openai/embo-01",
            "api_base": "https://api.minimax.io/v1",
            "dim": 1536,
        },
    ],
    "mistral": [
        {"model": "mistral-embed", "litellm": "mistral/mistral-embed", "dim": 1024},
    ],
    "gemini": [
        {"model": "text-embedding-004", "litellm": "gemini/text-embedding-004", "dim": 768},
    ],
    "cohere": [
        {"model": "embed-multilingual-v3.0", "litellm": "cohere/embed-multilingual-v3.0", "dim": 1024},
        {"model": "embed-english-v3.0", "litellm": "cohere/embed-english-v3.0", "dim": 1024},
    ],
    "openrouter": [
        {
            "model": "baai/bge-m3-20251117",
            "litellm": "openai/baai/bge-m3-20251117",
            "api_base": "https://openrouter.ai/api/v1",
            "dim": 1024,
        },
    ],
}

_PROVIDER_BY_MODEL: dict[str, str] = {
    entry["model"]: provider
    for provider, entries in EMBED_MODELS.items()
    for entry in entries
}
_BY_MODEL: dict[str, dict[str, Any]] = {
    entry["model"]: entry
    for entries in EMBED_MODELS.values()
    for entry in entries
}
_DYNAMIC_DIMS: dict[str, int] = {}
_PROVIDER_PREFIXES = {
    "openai": "openai/",
    "nvidia": "nvidia_nim/",
    "openrouter": "openrouter/",
    "ollama": "ollama/",
    "mistral": "mistral/",
    "gemini": "gemini/",
    "cohere": "cohere/",
}


def _provider_and_api_model(model: str) -> tuple[str, str]:
    """Löst kanonische Registry-ID in Provider und API-Modellnamen auf."""
    if model in _PROVIDER_BY_MODEL:
        return _PROVIDER_BY_MODEL[model], model
    for provider, prefix in _PROVIDER_PREFIXES.items():
        if model.startswith(prefix):
            return provider, model[len(prefix):]
    return "", model


def register_model_dimension(model: str, dim: int | None) -> None:
    if dim and dim > 0:
        _DYNAMIC_DIMS[model] = dim


def dim_for_model(model: str) -> int:
    if model in _DYNAMIC_DIMS:
        return _DYNAMIC_DIMS[model]
    if model in _BY_MODEL:
        return _BY_MODEL[model]["dim"]
    _, api_model = _provider_and_api_model(model)
    static_dim = _BY_MODEL.get(api_model, {}).get("dim", 0)
    if static_dim:
        return static_dim
    try:
        from hydrahive.llm._config import load_config
        return int((load_config().get("embed_dimensions") or {}).get(model, 0))
    except (TypeError, ValueError):
        return 0


def litellm_model(model: str) -> str:
    return _BY_MODEL[model]["litellm"] if model in _BY_MODEL else model
