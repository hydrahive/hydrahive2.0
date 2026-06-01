"""Gemeinsame Anthropic-Payload-Helfer für Stream- und Non-Stream-Pfad (#200).

Zentral, um Drift zwischen den beiden Backends zu vermeiden — analog zu
_token_usage.usage_dict. Vorher lagen diese Helfer dupliziert in
_llm_bridge_backends.py und _stream_providers.py; block_to_dict war bereits
gedriftet (Streaming-Variante verlor Daten von SDK-Objekten ohne model_dump).
"""
from __future__ import annotations

import json
from typing import Any


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
