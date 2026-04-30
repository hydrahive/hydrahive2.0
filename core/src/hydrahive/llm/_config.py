"""LLM-Config-Loading mit mtime-Cache und Provider-Key-Helpers."""
from __future__ import annotations

import json
import os

from hydrahive.settings import settings

_ENV_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "nvidia": "NVIDIA_NIM_API_KEY",
}

_config_cache: tuple[float, dict] | None = None


def load_config() -> dict:
    """LLM-Config mit mtime-basiertem Cache. Bei vielen parallelen Streams
    spart das die wiederholte Datei-Lese-IO. Cache invalidiert nur bei mtime-
    Änderung (z.B. nach LLM-Page-Save)."""
    global _config_cache
    path = settings.llm_config
    if not path.exists():
        return {"providers": [], "default_model": ""}
    mtime = path.stat().st_mtime
    if _config_cache and _config_cache[0] == mtime:
        return _config_cache[1]
    data = json.loads(path.read_text())
    _config_cache = (mtime, data)
    return data


def apply_keys(config: dict) -> None:
    """Setzt Provider-API-Keys als ENV-Vars für LiteLLM-Pfad."""
    for p in config.get("providers", []):
        key = p.get("api_key", "")
        pid = p.get("id", "")
        if not key:
            continue
        env = _ENV_MAP.get(pid)
        if env:
            os.environ[env] = key


def get_provider_key(config: dict, provider_id: str) -> str:
    for p in config.get("providers", []):
        if p.get("id") == provider_id:
            return p.get("api_key", "")
    return ""
