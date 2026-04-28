from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

import litellm

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True

_ENV_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def _load_config() -> dict:
    if not settings.llm_config.exists():
        return {"providers": [], "default_model": ""}
    return json.loads(settings.llm_config.read_text())


def _apply_keys(config: dict) -> None:
    for p in config.get("providers", []):
        env = _ENV_MAP.get(p.get("id", ""))
        if env and p.get("api_key"):
            os.environ[env] = p["api_key"]


def default_model() -> str:
    return _load_config().get("default_model", "")


async def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    cfg = _load_config()
    _apply_keys(cfg)
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")
    resp = await litellm.acompletion(
        model=target,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


async def stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    cfg = _load_config()
    _apply_keys(cfg)
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")
    resp = await litellm.acompletion(
        model=target,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
