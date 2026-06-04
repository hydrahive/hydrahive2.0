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

def provider_env_vars() -> set[str]:
    """ENV-Variablennamen unter denen apply_keys() die Provider-API-Keys ablegt.
    SSOT für jeden, der diese Keys schützen muss (z.B. die shell_exec-Denylist) —
    ein neuer Provider in _ENV_MAP ist damit automatisch abgedeckt."""
    return set(_ENV_MAP.values())


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


def openrouter_key() -> str:
    """OpenRouter-API-Key aus der Config (SSOT für alle Media-Tools)."""
    return get_provider_key(load_config(), "openrouter")


def get_provider_group_id(config: dict, provider_id: str) -> str:
    for p in config.get("providers", []):
        if p.get("id") == provider_id:
            return p.get("group_id", "")
    return ""


# Zweck → Storage-Pfad in llm.json. stt liegt historisch unter media_models.transcribe.
_PURPOSE_KEYS: dict[str, tuple[str, ...]] = {
    "chat": ("default_model",),
    "embed": ("embed_model",),
    "image": ("media_models", "image"),
    "music": ("media_models", "music"),
    "tts": ("media_models", "tts"),
    "stt": ("media_models", "transcribe"),
    "video": ("media_models", "video"),
}


def get_default(purpose: str) -> str:
    if purpose not in _PURPOSE_KEYS:
        raise ValueError(f"unbekannter Zweck: {purpose}")
    node: object = load_config()
    for k in _PURPOSE_KEYS[purpose]:
        node = node.get(k) if isinstance(node, dict) else None
    return node if isinstance(node, str) else ""


def set_default(purpose: str, model: str) -> None:
    global _config_cache
    if purpose not in _PURPOSE_KEYS:
        raise ValueError(f"unbekannter Zweck: {purpose}")
    path = settings.llm_config
    data = json.loads(path.read_text()) if path.exists() else {"providers": []}
    keys = _PURPOSE_KEYS[purpose]
    node = data
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = model
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    _config_cache = None  # Cache invalidieren, sonst liest load_config alt
