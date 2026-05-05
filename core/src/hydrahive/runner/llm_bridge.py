from __future__ import annotations

import logging

from hydrahive.llm import client as llm_client
from hydrahive.llm._config import apply_keys
from hydrahive.runner._codex_provider import codex_call
from hydrahive.runner._llm_bridge_backends import anthropic_call, litellm_call, minimax_anthropic_call

logger = logging.getLogger(__name__)


async def call_with_tools(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[list[dict], str]:
    """One non-streaming LLM call with tool support.

    Returns (content_blocks, stop_reason). Stop-reason values from Anthropic:
    'end_turn' | 'max_tokens' | 'stop_sequence' | 'tool_use' — the runner
    needs this to detect truncation (= broken tool_use inputs).
    """
    cfg = llm_client._load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if llm_client.is_minimax_model(target):
        minimax_key = llm_client._get_minimax_key(cfg)
        if not minimax_key:
            raise ValueError("MiniMax-API-Key fehlt — Provider 'minimax' in der LLM-Config setzen")
        return await minimax_anthropic_call(
            api_key=minimax_key,
            model=llm_client._strip_provider_prefix(target),
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    is_claude = llm_client._strip_provider_prefix(target).startswith("claude-")
    if is_claude:
        # OAuth-fähig: erst frischen Token holen (refresht automatisch wenn nötig)
        from hydrahive.oauth.anthropic import resolve_anthropic_token
        anthropic_key = await resolve_anthropic_token()
        if not anthropic_key:
            raise ValueError("Anthropic-Auth fehlt — API-Key oder OAuth-Login auf der LLM-Seite")
        return await anthropic_call(
            key=anthropic_key,
            model=llm_client._strip_provider_prefix(target),
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # OpenAI-Provider mit OAuth-Block → Codex-Backend (chatgpt.com), nicht LiteLLM.
    # Nur wenn das Modell zu OpenAI gehört (openai/-Prefix) UND ein OAuth-Token
    # da ist. Ansonsten Fall-through zu LiteLLM (api_key-Pfad).
    if target.startswith("openai/"):
        from hydrahive.oauth.openai_codex import resolve_openai_codex_token
        codex_token = await resolve_openai_codex_token()
        if codex_token.get("access"):
            return await codex_call(
                access_token=codex_token["access"],
                account_id=codex_token.get("account_id", ""),
                model=target[len("openai/"):],
                system_prompt=system_prompt,
                messages=messages,
                tools=tools,
            )

    # Alle anderen Provider (OpenAI mit API-Key, NVIDIA, Groq, Mistral, Gemini,
    # OpenRouter, …) gehen über LiteLLM. apply_keys setzt die ENV-Variablen aus
    # llm.json.
    apply_keys(cfg)
    return await litellm_call(
        model=target,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )
