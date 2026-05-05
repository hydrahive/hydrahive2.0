"""LLM-Modell-Catalog: Live-Listing pro Provider + interne Metadata.

Per Provider hat HH2 eine Liste der gepflegten Metadata (context_window,
tool_use, category, params, hint). Beim Catalog-Aufruf wird live von der
Provider-API die Modell-Liste geholt und mit dieser Metadata gejoint.

Modelle die live verfügbar sind aber nicht in der Metadata stehen, kommen
trotzdem in die Liste — mit `metadata.unknown=True`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Provider-Endpoints zum Live-Modell-Listing.
# Format: provider_id → {url, auth_kind ("bearer"|"query"), query_param}
_PROVIDER_ENDPOINTS = {
    "openai":     {"url": "https://api.openai.com/v1/models", "auth": "bearer"},
    "nvidia":     {"url": "https://integrate.api.nvidia.com/v1/models", "auth": "bearer"},
    "groq":       {"url": "https://api.groq.com/openai/v1/models", "auth": "bearer"},
    "mistral":    {"url": "https://api.mistral.ai/v1/models", "auth": "bearer"},
    "openrouter": {"url": "https://openrouter.ai/api/v1/models", "auth": "bearer"},
    "gemini":     {"url": "https://generativelanguage.googleapis.com/v1beta/models",
                   "auth": "query", "query_param": "key"},
    # Anthropic + MiniMax haben kein public /v1/models-Endpoint → static
    "anthropic":  {"url": None, "auth": None},
    "minimax":    {"url": None, "auth": None},
}

# Static-Listen für Provider ohne /v1/models-Endpoint.
_STATIC_MODELS = {
    "anthropic": [
        "claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5",
        "claude-sonnet-4-5", "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022",
    ],
    "minimax": ["MiniMax-M2", "MiniMax-M2.7", "abab6.5s-chat"],
}

# Modell-Prefix für LiteLLM bei Provider die das brauchen.
_PROVIDER_PREFIX = {
    "openai": "openai/", "nvidia": "nvidia_nim/", "groq": "groq/",
    "mistral": "mistral/", "openrouter": "openrouter/", "gemini": "gemini/",
}

# Interne Metadata-Tabelle. Per Modell-ID (mit Prefix) → Eigenschaften.
# tool_use: True/False/None (None = ungetestet/unbekannt).
_METADATA: dict[str, dict[str, Any]] = {
    # Anthropic
    "claude-opus-4-7":   {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-sonnet-4-6": {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-sonnet-4-5": {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-haiku-4-5":  {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-3-7-sonnet-20250219": {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-3-5-haiku-20241022":  {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    # MiniMax
    "MiniMax-M2":   {"context_window": 256_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "MiniMax-M2.7": {"context_window": 256_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "abab6.5s-chat":{"context_window": 245_000, "tool_use": True, "category": "chat", "family": "minimax"},
    # NVIDIA NIM — empirisch verifiziert wo möglich
    "nvidia_nim/qwen/qwen2.5-coder-32b-instruct": {"context_window": 32_000, "tool_use": False, "category": "code", "family": "qwen", "params": "32B"},
    "nvidia_nim/qwen/qwen3-next-80b-a3b-instruct": {"context_window": 262_144, "tool_use": True, "category": "chat", "family": "qwen", "params": "80B"},
    "nvidia_nim/qwen/qwen3-next-80b-a3b-thinking": {"context_window": 262_144, "tool_use": True, "category": "reasoning", "family": "qwen", "params": "80B"},
    "nvidia_nim/qwen/qwen3-coder-480b-a35b-instruct": {"context_window": 262_144, "tool_use": True, "category": "code", "family": "qwen", "params": "480B"},
    "nvidia_nim/qwen/qwen3.5-122b-a10b": {"context_window": 262_144, "tool_use": True, "category": "chat", "family": "qwen", "params": "122B"},
    "nvidia_nim/qwen/qwen3.5-397b-a17b": {"context_window": 262_144, "tool_use": True, "category": "chat", "family": "qwen", "params": "397B"},
    "nvidia_nim/meta/llama-3.3-70b-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "llama", "params": "70B"},
    "nvidia_nim/meta/llama-3.1-405b-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "llama", "params": "405B"},
    "nvidia_nim/meta/llama-3.1-70b-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "llama", "params": "70B"},
    "nvidia_nim/meta/llama-3.1-8b-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "llama", "params": "8B"},
    "nvidia_nim/meta/llama-3.2-90b-vision-instruct": {"context_window": 128_000, "tool_use": True, "category": "vision", "family": "llama", "params": "90B"},
    "nvidia_nim/meta/llama-3.2-11b-vision-instruct": {"context_window": 128_000, "tool_use": True, "category": "vision", "family": "llama", "params": "11B"},
    "nvidia_nim/meta/llama-4-maverick-17b-128e-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "llama", "params": "17B-MoE"},
    "nvidia_nim/deepseek-ai/deepseek-v4-pro": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "deepseek", "params": "?"},
    "nvidia_nim/deepseek-ai/deepseek-v4-flash": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "deepseek", "params": "?"},
    "nvidia_nim/moonshotai/kimi-k2-thinking": {"context_window": 128_000, "tool_use": True, "category": "reasoning", "family": "kimi"},
    "nvidia_nim/moonshotai/kimi-k2.6": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "kimi"},
    "nvidia_nim/openai/gpt-oss-120b": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "gpt-oss", "params": "120B"},
    "nvidia_nim/openai/gpt-oss-20b": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "gpt-oss", "params": "20B"},
    "nvidia_nim/mistralai/mistral-large-3-675b-instruct-2512": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "mistral", "params": "675B"},
    "nvidia_nim/mistralai/mistral-large-2-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "mistral", "params": "123B"},
    "nvidia_nim/mistralai/codestral-22b-instruct-v0.1": {"context_window": 32_000, "tool_use": False, "category": "code", "family": "mistral", "params": "22B"},
    # Embed-Modelle (separat)
    "nvidia_nim/nvidia/nv-embed-v1": {"context_window": 32_000, "tool_use": False, "category": "embed", "family": "nvidia"},
    "nvidia_nim/nvidia/nv-embedqa-e5-v5": {"context_window": 512, "tool_use": False, "category": "embed", "family": "nvidia"},
    # OpenAI
    "openai/gpt-5":      {"context_window": 400_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/gpt-5-mini": {"context_window": 400_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/gpt-4o":     {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/gpt-4o-mini":{"context_window": 128_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/o1-preview": {"context_window": 128_000, "tool_use": False, "category": "reasoning", "family": "gpt"},
    "openai/o1-mini":    {"context_window": 128_000, "tool_use": False, "category": "reasoning", "family": "gpt"},
}


def _normalize_id(provider_id: str, raw_id: str) -> str:
    """Live-API gibt 'meta/llama-...' — wir schreiben 'nvidia_nim/meta/llama-...'."""
    prefix = _PROVIDER_PREFIX.get(provider_id, "")
    if prefix and not raw_id.startswith(prefix):
        return prefix + raw_id
    return raw_id


async def _fetch_live_models(provider_id: str, api_key: str) -> list[str]:
    """Holt die Modell-Liste live vom Provider. Bei Fehler: leere Liste, Warning."""
    cfg = _PROVIDER_ENDPOINTS.get(provider_id, {})
    url = cfg.get("url")
    if not url or not api_key:
        return list(_STATIC_MODELS.get(provider_id, []))
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if cfg["auth"] == "bearer":
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            else:  # query
                param = cfg.get("query_param", "key")
                resp = await client.get(url, params={param: api_key})
            resp.raise_for_status()
            data = resp.json()
        # OpenAI/NVIDIA/Mistral/Groq: {"data": [{"id": ...}]}
        # Gemini: {"models": [{"name": "models/..."}]}
        if isinstance(data.get("data"), list):
            ids = [m.get("id", "") for m in data["data"] if m.get("id")]
        elif isinstance(data.get("models"), list):
            ids = [m.get("name", "").replace("models/", "") for m in data["models"] if m.get("name")]
        else:
            ids = []
        # Provider-Prefix + dedup
        normalized = sorted({_normalize_id(provider_id, i) for i in ids if i})
        return normalized
    except Exception as e:
        logger.warning("Catalog: live-fetch für %s fehlgeschlagen: %s", provider_id, e)
        return []


def _enrich(provider_id: str, model_id: str) -> dict[str, Any]:
    """Joint Modell-ID mit Metadata. Unbekannt → unknown:True."""
    md = _METADATA.get(model_id)
    if md:
        return {"id": model_id, **md, "unknown": False}
    return {
        "id": model_id,
        "context_window": None,
        "tool_use": None,
        "category": "chat",
        "family": "?",
        "unknown": True,
    }


async def catalog_for_providers(providers: list[dict]) -> list[dict]:
    """Erzeugt Catalog-Einträge pro konfiguriertem Provider parallel.

    `providers` ist die Liste aus llm.json (jeweils {id, api_key, oauth, ...}).
    """
    async def one(p: dict) -> dict:
        pid = p.get("id", "")
        key = p.get("api_key", "") or (p.get("oauth") or {}).get("access", "")
        ids = await _fetch_live_models(pid, key)
        if not ids:
            ids = list(_STATIC_MODELS.get(pid, []))
        models = [_enrich(pid, mid) for mid in ids]
        return {
            "provider_id": pid,
            "provider_name": p.get("name", pid),
            "configured": bool(key),
            "models": models,
            "live_count": len(ids),
        }
    return await asyncio.gather(*[one(p) for p in providers])
