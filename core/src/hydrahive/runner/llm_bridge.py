from __future__ import annotations

import logging

from hydrahive.llm import client as llm_client
from hydrahive.runner._llm_bridge_backends import anthropic_call, minimax_anthropic_call

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

    anthropic_key = llm_client._get_anthropic_key(cfg)
    is_claude = llm_client._strip_provider_prefix(target).startswith("claude-")
    if not is_claude or not anthropic_key:
        raise NotImplementedError("Nur Anthropic- und MiniMax-Pfad implementiert.")

    return await anthropic_call(
        key=anthropic_key,
        model=llm_client._strip_provider_prefix(target),
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )
