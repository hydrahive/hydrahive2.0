"""Gemeinsame Anthropic-Payload-Helfer für Stream- und Non-Stream-Pfad (#200).

Zentral, um Drift zwischen den beiden Backends zu vermeiden — analog zu
_token_usage.usage_dict. Vorher lagen diese Helfer dupliziert in
_llm_bridge_backends.py und _stream_providers.py; block_to_dict war bereits
gedriftet (Streaming-Variante verlor Daten von SDK-Objekten ohne model_dump).
"""
from __future__ import annotations

import json
from typing import Any

from hydrahive.llm import client as llm_client


def cache_control(ttl: str) -> dict:
    ctrl: dict[str, Any] = {"type": "ephemeral"}
    if ttl and ttl != "5m":
        ctrl["ttl"] = ttl
    return ctrl


def with_cache_breakpoint(messages: list[dict], ttl: str = "5m") -> list[dict]:
    """Markiert den letzten Content-Block der LETZTEN Message als Cache-Breakpoint.

    Quelle: claude-code-source-code/src/services/api/claude.ts:3089
        `const markerIndex = skipCacheWrite ? messages.length - 2 : messages.length - 1`

    Default-Pfad ist `messages.length - 1` (last message). Marker auf [-1] hält
    die local-attention KV-pages refcount-geschützt (Mycro turn-to-turn
    eviction) — der Cache überlebt einen Turn länger als bei [-2].

    Default-TTL = "5m" (Anthropic-Default).
    """
    if not messages:
        return messages
    msgs = list(messages)
    target = msgs[-1]
    content = target.get("content", [])
    if not isinstance(content, list) or not content:
        # content als String (alte API-Form) → in list konvertieren
        if isinstance(content, str) and content:
            return [*msgs[:-1], {**target, "content": [
                {"type": "text", "text": content, "cache_control": cache_control(ttl)},
            ]}]
        return msgs
    last_block = content[-1]
    if not isinstance(last_block, dict):
        return msgs
    new_content = list(content)
    new_content[-1] = {**last_block, "cache_control": cache_control(ttl)}
    msgs[-1] = {**target, "content": new_content}
    return msgs


def add_cache_reference_to_tool_results(messages: list[dict]) -> list[dict]:
    """DEAKTIVIERT — cache_reference ist Anthropic-Beta (cache-editing) und
    braucht einen Beta-Header, den wir nicht haben (sonst API-Error 400).

    Portiert von Claude Code (claude.ts:3164-3207). Bleibt für die Zukunft hier,
    wird aber aktuell NICHT aufgerufen.
    """
    last_cc_idx = -1
    for i, msg in enumerate(messages):
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and "cache_control" in block:
                last_cc_idx = i  # last-write-wins — nur der letzte zählt

    if last_cc_idx < 0:
        return messages

    result = list(messages)
    for i in range(last_cc_idx):
        msg = result[i]
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        new_content = list(content)
        modified = False
        for j, block in enumerate(new_content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_use_id = block.get("tool_use_id")
            if not tool_use_id:
                continue
            new_content[j] = {**block, "cache_reference": tool_use_id}
            modified = True
        if modified:
            result[i] = {**msg, "content": new_content}
    return result


def block_to_dict(block: Any) -> dict:
    """Anthropic-SDK liefert typisierte Objekte; für DB-Storage zu Plain-Dicts
    normalisieren. Vier Stufen, damit auch SDK-Objekte OHNE model_dump (z.B. ein
    alter ThinkingBlock) verlustfrei serialisiert werden statt als Stub."""
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if hasattr(block, "dict"):
        return block.dict()
    if isinstance(block, dict):
        return block
    return json.loads(json.dumps(block, default=lambda o: getattr(o, "__dict__", str(o))))


def strip_minimax_cache_control(messages: list[dict], tools: list[dict]) -> tuple[list[dict], list[dict]]:
    """Entfernt cache_control aus Messages und Tools — MiniMax wirft sonst HTTP 500."""
    clean: list[dict] = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            stripped = [{k: v for k, v in b.items() if k != "cache_control"} for b in content]
            clean.append({**msg, "content": stripped})
        else:
            clean.append(msg)
    clean_tools = [{k: v for k, v in t.items() if k != "cache_control"} for t in tools]
    return clean, clean_tools


def build_anthropic_kwargs(
    *, key: str, model: str, system_prompt: str,
    volatile_system: str | None, summary_system: str | None, cache_ttl: str,
    messages: list[dict], tools: list[dict], temperature: float, max_tokens: int,
    reasoning_effort: str | None,
) -> tuple[Any, dict[str, Any]]:
    """Baut (AsyncAnthropic-Client, kwargs) für einen Anthropic-Call.

    Single-Source für Stream- UND Non-Stream-Pfad (#200). Hier lebt die delikate
    Cache-Ordering: OAuth-Identity zuerst, dann system_prompt+summary mit
    cache_control, volatile_system OHNE cache_control ans Ende (sonst bricht der
    Prompt-Cache), Breakpoint auf der letzten Message, cache_control nur am
    letzten Tool. apply_effort wird mit angewendet. Die Aufrufer unterscheiden
    sich danach nur in .create() vs .stream() + dem temperature-Retry.
    """
    import anthropic as _anthropic
    from hydrahive.llm._anthropic import apply_effort

    is_oauth = key.startswith("sk-ant-oat")
    if is_oauth:
        client = _anthropic.AsyncAnthropic(
            api_key="", auth_token=key, timeout=300.0,
            default_headers=llm_client._ANTHROPIC_OAUTH_HEADERS,
        )
    else:
        client = _anthropic.AsyncAnthropic(api_key=key, timeout=300.0)

    system_blocks: list[dict[str, Any]] = []
    if is_oauth:
        system_blocks.append({"type": "text", "text": llm_client._ANTHROPIC_OAUTH_IDENTITY[0]["text"]})
    if system_prompt:
        system_blocks.append({"type": "text", "text": system_prompt, "cache_control": cache_control(cache_ttl)})
    elif system_blocks:
        system_blocks[0]["cache_control"] = cache_control(cache_ttl)
    if summary_system:
        system_blocks.append({"type": "text", "text": summary_system, "cache_control": cache_control(cache_ttl)})
    if volatile_system:
        system_blocks.append({"type": "text", "text": volatile_system})

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": with_cache_breakpoint(messages, ttl=cache_ttl),
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_blocks:
        kwargs["system"] = system_blocks
    if tools:
        kwargs["tools"] = [*tools[:-1], {**tools[-1], "cache_control": cache_control(cache_ttl)}]

    apply_effort(kwargs, model, reasoning_effort)
    return client, kwargs


def build_minimax_kwargs(
    *, api_key: str, model: str, system_prompt: str,
    volatile_system: str | None, summary_system: str | None,
    messages: list[dict], tools: list[dict], temperature: float, max_tokens: int,
    reasoning_effort: str | None,
) -> tuple[Any, dict[str, Any]]:
    """Baut (AsyncAnthropic-Client gegen MiniMax, kwargs). Single-Source für
    Stream + Non-Stream. cache_control wird entfernt (MiniMax → HTTP 500), system
    als EIN String (Array mit mehreren Blöcken bricht nach Compaction)."""
    import anthropic as _anthropic
    from hydrahive.llm._anthropic import apply_effort

    client = _anthropic.AsyncAnthropic(
        base_url=llm_client.MINIMAX_BASE_URL, api_key=api_key, timeout=300.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    messages, tools = strip_minimax_cache_control(messages, tools)
    kwargs: dict[str, Any] = {
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    }
    if system_prompt or summary_system or volatile_system:
        parts = [p for p in [system_prompt, summary_system, volatile_system] if p]
        kwargs["system"] = "\n\n".join(parts)
    if tools:
        kwargs["tools"] = tools

    apply_effort(kwargs, model, reasoning_effort)
    return client, kwargs
