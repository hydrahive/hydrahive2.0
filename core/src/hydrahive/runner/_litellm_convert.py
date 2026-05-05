"""Konverter zwischen HH2-internem (Anthropic-Stil) und OpenAI/LiteLLM-Format.

HH2 spricht intern Anthropic-Format (tool_use-Blocks, content-Listen).
LiteLLM erwartet OpenAI-Format (tool_calls, role:tool, function-Schema).

Nur die Mappings — kein HTTP-Code, keine Provider-Logik.
"""
from __future__ import annotations

import json
import uuid
from typing import Any


def tools_to_openai(tools: list[dict]) -> list[dict]:
    """Anthropic-Tool-Schema → OpenAI-Function-Schema.

    Anthropic: {"name": "x", "description": "...", "input_schema": {...}}
    OpenAI:    {"type": "function", "function": {"name": "x", "description": "...", "parameters": {...}}}
    """
    out = []
    for t in tools or []:
        out.append({
            "type": "function",
            "function": {
                "name": t.get("name", ""),
                "description": t.get("description", "") or "",
                "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
            },
        })
    return out


def messages_to_openai(messages: list[dict], system_prompt: str = "") -> list[dict]:
    """Anthropic-messages → OpenAI-messages.

    Mappings:
    - {"role":"user","content":"text"} → {"role":"user","content":"text"}
    - {"role":"assistant","content":[text-blocks + tool_use-blocks]}
        → {"role":"assistant","content":"joined text","tool_calls":[...]}
    - {"role":"user","content":[tool_result-blocks]}
        → mehrere {"role":"tool","tool_call_id":"...","content":"..."}-Messages
    """
    out: list[dict] = []
    if system_prompt:
        out.append({"role": "system", "content": system_prompt})

    for m in messages:
        role = m.get("role", "")
        content = m.get("content")

        # User mit String-Content
        if role == "user" and isinstance(content, str):
            out.append({"role": "user", "content": content})
            continue

        # User mit Block-Liste — kann text, image, tool_result enthalten
        if role == "user" and isinstance(content, list):
            tool_results = []
            text_parts = []
            image_parts = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                btype = b.get("type")
                if btype == "tool_result":
                    tc_id = b.get("tool_use_id", "")
                    inner = b.get("content")
                    if isinstance(inner, list):
                        text = "".join(x.get("text", "") for x in inner if isinstance(x, dict) and x.get("type") == "text")
                    else:
                        text = inner if isinstance(inner, str) else json.dumps(inner)
                    tool_results.append({"role": "tool", "tool_call_id": tc_id, "content": text or ""})
                elif btype == "text":
                    text_parts.append(b.get("text", ""))
                elif btype == "image":
                    src = b.get("source") or {}
                    data = src.get("data", "")
                    mime = src.get("media_type") or "image/png"
                    image_parts.append({"type": "image_url",
                                        "image_url": {"url": f"data:{mime};base64,{data}"}})
            if tool_results:
                # tool-Results als eigene Messages emittieren (vor dem User-Text)
                out.extend(tool_results)
            if text_parts or image_parts:
                user_content: Any
                if image_parts:
                    user_content = ([{"type": "text", "text": "".join(text_parts)}]
                                    if text_parts else []) + image_parts
                else:
                    user_content = "".join(text_parts)
                out.append({"role": "user", "content": user_content})
            continue

        # Assistant mit Block-Liste — text + tool_use
        if role == "assistant" and isinstance(content, list):
            text_parts = []
            tool_calls = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                btype = b.get("type")
                if btype == "text":
                    text_parts.append(b.get("text", ""))
                elif btype == "tool_use":
                    tool_calls.append({
                        "id": b.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": b.get("name", ""),
                            "arguments": json.dumps(b.get("input") or {}),
                        },
                    })
            msg: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts) or None}
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
            continue

        # Assistant mit String-Content
        if role == "assistant" and isinstance(content, str):
            out.append({"role": "assistant", "content": content})
            continue

    return out


def openai_response_to_anthropic_blocks(message: Any) -> list[dict]:
    """LiteLLM/OpenAI assistant-message → Anthropic-Content-Blocks.

    `message` hat .content (string|None) und .tool_calls (list).
    Liefert Blocks im Anthropic-Format: text, tool_use.
    """
    blocks: list[dict] = []
    text = getattr(message, "content", None) or ""
    if text:
        blocks.append({"type": "text", "text": text})

    tool_calls = getattr(message, "tool_calls", None) or []
    for tc in tool_calls:
        # tc kann pydantic-Model oder dict sein
        if hasattr(tc, "function"):
            fn = tc.function
            name = getattr(fn, "name", "") or ""
            args_raw = getattr(fn, "arguments", "") or "{}"
            tc_id = getattr(tc, "id", "") or f"toolu_{uuid.uuid4().hex[:16]}"
        else:
            fn = tc.get("function", {}) or {}
            name = fn.get("name", "")
            args_raw = fn.get("arguments", "{}")
            tc_id = tc.get("id") or f"toolu_{uuid.uuid4().hex[:16]}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
        except json.JSONDecodeError:
            args = {"_raw_arguments": args_raw}
        blocks.append({"type": "tool_use", "id": tc_id, "name": name, "input": args})
    return blocks


# OpenAI/LiteLLM finish_reason → Anthropic stop_reason
_STOP_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "content_filter": "stop_sequence",
}


def openai_stop_to_anthropic(reason: str) -> str:
    return _STOP_MAP.get(reason or "", reason or "end_turn")
