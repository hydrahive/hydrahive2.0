"""Embedding-Modelle: Lookup-Table + LiteLLM-Wrapper.

Nur explizit bekannte Modelle werden angeboten — Dimension ist dadurch immer bekannt.
Provider mit api_base nutzen den openai-Client direkt (NVIDIA, MiniMax).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# provider_id → bekannte Embedding-Modelle mit Dimension und LiteLLM-Modell-String
# api_base: für Provider die OpenAI-kompatibel laufen aber eine eigene Base-URL haben
EMBED_MODELS: dict[str, list[dict[str, Any]]] = {
    "openai": [
        {"model": "text-embedding-3-small", "litellm": "text-embedding-3-small", "dim": 1536},
        {"model": "text-embedding-3-large", "litellm": "text-embedding-3-large", "dim": 3072},
        {"model": "text-embedding-ada-002",  "litellm": "text-embedding-ada-002",  "dim": 1536},
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
        {"model": "embed-english-v3.0",      "litellm": "cohere/embed-english-v3.0",      "dim": 1024},
    ],
}

# provider_id für jeden Modell-String — für Key-Lookup
_PROVIDER_BY_MODEL: dict[str, str] = {
    e["model"]: pid
    for pid, entries in EMBED_MODELS.items()
    for e in entries
}

_BY_MODEL: dict[str, dict[str, Any]] = {
    e["model"]: e
    for entries in EMBED_MODELS.values()
    for e in entries
}


def dim_for_model(model: str) -> int:
    return _BY_MODEL[model]["dim"] if model in _BY_MODEL else 0


def litellm_model(model: str) -> str:
    return _BY_MODEL[model]["litellm"] if model in _BY_MODEL else model


def available_for_config(config: dict) -> list[dict]:
    """Gibt Embedding-Modelle zurück für die ein API-Key konfiguriert ist."""
    result = []
    for p in config.get("providers", []):
        pid = p.get("id", "")
        if p.get("api_key") and pid in EMBED_MODELS:
            for entry in EMBED_MODELS[pid]:
                result.append({
                    "model": entry["model"],
                    "dim": entry["dim"],
                    "provider": pid,
                })
    return result


async def aembed(text: str, model: str) -> list[float] | None:
    """Erzeugt einen Embedding-Vektor. Gibt None bei Fehler zurück."""
    results = await aembed_batch([text], model)
    return results[0] if results else None


async def aembed_batch(texts: list[str], model: str) -> list[list[float] | None]:
    """Bettet mehrere Texte in einem einzigen API-Call ein.

    Provider mit api_base (z.B. NVIDIA NIM) nutzen den openai-Client direkt —
    LiteLLM konstruiert URLs für custom-base-URL-Provider nicht korrekt.
    """
    from hydrahive.llm._config import apply_keys, get_provider_key, load_config
    if not texts:
        return []
    try:
        entry = _BY_MODEL.get(model, {})
        config = load_config()

        if entry.get("api_base"):
            import openai
            provider = _PROVIDER_BY_MODEL.get(model, "")
            key = get_provider_key(config, provider)
            client = openai.AsyncOpenAI(api_key=key, base_url=entry["api_base"])
            # Provider-Prefix (z.B. "minimax/") für den API-Call entfernen
            api_model = model.split("/", 1)[-1] if "/" in model else model
            resp = await client.embeddings.create(model=api_model, input=texts)
            ordered = sorted(resp.data, key=lambda d: d.index)
            return [list(d.embedding) for d in ordered]
        else:
            import litellm
            apply_keys(config)
            resp = await litellm.aembedding(model=litellm_model(model), input=texts)
            return [d["embedding"] for d in resp.data]
    except Exception as e:
        logger.warning("Batch-Embedding fehlgeschlagen (model=%s, n=%d): %s", model, len(texts), e)
        return [None] * len(texts)
