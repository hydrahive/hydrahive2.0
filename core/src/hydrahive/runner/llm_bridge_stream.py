"""Streaming-Variant des LLM-Calls.

Yields rohe Anthropic-Stream-Events. Caller (runner) macht das Mapping auf
unsere Event-Klassen + Block-Akkumulation."""
from __future__ import annotations

import logging
from typing import AsyncIterator

from hydrahive.llm import client as llm_client
from hydrahive.runner._codex_provider import codex_stream
from hydrahive.runner._stream_providers import anthropic_stream, minimax_stream

logger = logging.getLogger(__name__)


class StreamingNotSupported(RuntimeError):
    """Wird vom Caller gefangen → fallback auf non-streaming."""


async def stream_with_tools(
    *,
    model: str,
    system_prompt: str,
    volatile_system: str | None = None,
    cache_ttl: str = "1h",
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
) -> AsyncIterator[dict]:
    """Yields normalized stream events as dicts.

    Event-Format:
      {"type": "message_start"}
      {"type": "block_start", "index": 0, "block_type": "text"}
      {"type": "block_start", "index": 1, "block_type": "tool_use", "id": "...", "name": "..."}
      {"type": "text_delta", "index": 0, "text": "..."}
      {"type": "input_delta", "index": 1, "json_partial": "..."}
      {"type": "block_stop", "index": 0}
      {"type": "message_stop", "stop_reason": "end_turn", "blocks": [...]}

    Bei Provider-Inkompatibilität: StreamingNotSupported geworfen — caller fallback.
    """
    cfg = llm_client._load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if llm_client.is_minimax_model(target):
        minimax_key = llm_client._get_minimax_key(cfg)
        if not minimax_key:
            raise StreamingNotSupported("MiniMax-API-Key fehlt")
        async for ev in minimax_stream(
            api_key=minimax_key,
            model=llm_client._strip_provider_prefix(target),
            system_prompt=system_prompt,
            volatile_system=volatile_system,
            cache_ttl=cache_ttl,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        ):
            yield ev
        return

    if target.startswith("openai-codex/"):
        from hydrahive.oauth.openai_codex import resolve_openai_codex_token
        codex_token = await resolve_openai_codex_token()
        if not codex_token.get("access"):
            raise StreamingNotSupported("ChatGPT Plus/Pro OAuth fehlt")
        async for ev in codex_stream(
            access_token=codex_token["access"],
            account_id=codex_token.get("account_id", ""),
            model=target[len("openai-codex/"):],
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
        ):
            yield ev
        return

    is_claude = llm_client._strip_provider_prefix(target).startswith("claude-")
    if not is_claude:
        raise StreamingNotSupported("Streaming nur für Anthropic + MiniMax + OpenAI-Codex implementiert")
    # OAuth-fähig: erst frischen Token holen (refresht automatisch wenn nötig)
    from hydrahive.oauth.anthropic import resolve_anthropic_token
    anthropic_key = await resolve_anthropic_token()
    if not anthropic_key:
        raise StreamingNotSupported("Anthropic-Auth fehlt — API-Key oder OAuth-Login auf /llm")

    async for ev in anthropic_stream(
        key=anthropic_key,
        model=llm_client._strip_provider_prefix(target),
        system_prompt=system_prompt,
        volatile_system=volatile_system,
        cache_ttl=cache_ttl,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    ):
        yield ev
