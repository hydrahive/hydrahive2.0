"""Central backend model-to-provider resolver for API metadata."""
from __future__ import annotations

from hydrahive.llm._config import load_config

_LOCAL_PROVIDERS = {"local", "ollama", "llamacpp", "lmstudio", "vllm"}
_KNOWN_PROVIDERS = {"anthropic", "openai", "minimax", "openrouter", "local"}


def _normalize_provider(provider: str) -> str:
    pid = (provider or "").strip().lower()
    if pid in _LOCAL_PROVIDERS:
        return "local"
    if pid in _KNOWN_PROVIDERS:
        return pid
    return pid or "unknown"


def provider_for_model(model: str | None) -> str:
    mid = (model or "").strip()
    if not mid:
        return "unknown"

    config = load_config()
    for provider in config.get("providers", []):
        models = provider.get("models", []) or []
        if mid in models:
            return _normalize_provider(provider.get("id", ""))

    if mid.startswith(("claude-", "anthropic/claude-")):
        return "anthropic"
    if mid.startswith(("gpt-", "o1", "o3", "o4", "openai/")):
        return "openai"
    if mid.lower().startswith(("minimax", "abab")):
        return "minimax"
    if mid.startswith(("ollama/", "local/")):
        return "local"
    if "/" in mid:
        return "openrouter"
    return "unknown"
