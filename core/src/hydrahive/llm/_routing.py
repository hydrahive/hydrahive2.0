"""Ziel eines LiteLLM-Aufrufs: eigene Adresse des Anbieters (api_base) und Ollama-Kontextfenster.

Gemeinsam für den Agenten-Chat (runner/llm_bridge.py) und llm.client complete()/stream()
(docs/specs/llm-client-api-base.md). Liegt in `llm`, damit `llm` nicht von `runner` abhängt.
"""
from __future__ import annotations

from hydrahive.llm._config import provider_api_base


def api_base_for(cfg: dict, model: str) -> str | None:
    """api_base des Anbieters, zu dem `model` gehört (über den Präfix, z. B. "ollama/").

    None, wenn kein Anbieter mit eingetragener Adresse passt – Cloud-Anbieter behalten ihr normales Ziel."""
    from hydrahive.llm._catalog_data import PROVIDER_PREFIX
    for provider_id, prefix in PROVIDER_PREFIX.items():
        if prefix and model.startswith(prefix):
            base = provider_api_base(cfg, provider_id)
            if base:
                return base
    return None


def litellm_target(cfg: dict, model: str) -> dict:
    """Zusätzliche Argumente für litellm.acompletion: api_base (falls eingetragen) und für Ollama num_ctx.

    Ohne Adresse und ohne Ollama ein leeres dict – dann bleibt der Aufruf genau wie früher."""
    extra: dict = {}
    base = api_base_for(cfg, model)
    if base:
        extra["api_base"] = base
    if model.startswith("ollama/"):
        from hydrahive.compaction.tokens import context_window_for
        from hydrahive.llm._config import num_ctx_for_ollama
        num_ctx = num_ctx_for_ollama(context_window_for(model))
        extra["num_ctx"] = num_ctx
        extra["extra_body"] = {"options": {"num_ctx": num_ctx}}
    return extra
