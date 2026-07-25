"""Backend-Registry + Resolver.

Mappt eine Modell-ID auf den zuständigen Adapter:
- "local:<provider_id>/<model>" → lokales Backend (Typ aus media_backends-Config)
- alles andere                   → OpenRouter (Default, Rückwärtskompatibilität)

E1 registriert nur OpenRouter. Weitere Adaptertypen (comfyui, switch-http)
kommen in E2/E4 dazu — hier ist der Erweiterungspunkt (_ADAPTERS).
"""
from __future__ import annotations

from hydrahive.llm.video_backends._base import VideoBackend
from hydrahive.llm.video_backends._comfyui import ComfyUIVideoBackend
from hydrahive.llm.video_backends._openrouter import OpenRouterVideoBackend

LOCAL_PREFIX = "local:"

# Adapter-Fabriken je Backend-Typ. E4 ergänzt "switch-http".
_ADAPTERS: dict[str, type] = {
    "openrouter": OpenRouterVideoBackend,
    "comfyui": ComfyUIVideoBackend,
}

_openrouter_singleton = OpenRouterVideoBackend()


def _media_backends(config: dict) -> list[dict]:
    """Liste der konfigurierten lokalen Media-Backends aus llm.json."""
    return config.get("media_backends", []) or []


def find_media_backend(config: dict, provider_id: str) -> dict | None:
    for b in _media_backends(config):
        if b.get("id", "") == provider_id:
            return b
    return None


def _backend_for_type(btype: str) -> VideoBackend | None:
    cls = _ADAPTERS.get(btype)
    return cls() if cls else None


def resolve_backend(model_id: str, config: dict) -> tuple[VideoBackend, dict]:
    """Findet (Backend-Adapter, Provider-Config) für eine Modell-ID.

    Rückwärtskompatibel: eine ID ohne `local:`-Prefix geht immer an OpenRouter,
    mit einem synthetischen leeren Provider-Dict.

    Raises:
        ValueError: local:-ID, deren Provider/Typ nicht (mehr) konfiguriert ist.
    """
    if not model_id.startswith(LOCAL_PREFIX):
        return _openrouter_singleton, {}

    # local:<provider_id>/<rest>
    rest = model_id[len(LOCAL_PREFIX):]
    provider_id, _, _ = rest.partition("/")
    provider = find_media_backend(config, provider_id)
    if provider is None:
        raise ValueError(f"Kein Media-Backend '{provider_id}' konfiguriert")
    btype = provider.get("type", "")
    backend = _backend_for_type(btype)
    if backend is None:
        raise ValueError(f"Unbekannter Media-Backend-Typ '{btype}' (Provider {provider_id})")
    return backend, provider
