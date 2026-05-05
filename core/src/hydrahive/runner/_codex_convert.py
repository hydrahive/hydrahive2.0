"""Konverter zwischen HH2-internem (Anthropic-Stil) und OpenAI Responses-API.

Responses-API ist nicht Chat-Completions — Items werden flach im `input`-Array
emittiert (function_call und function_call_output sind keine Rollen, sondern
Top-Level-Items). System-Prompt landet in `instructions`.
"""
from __future__ import annotations

import json
from typing import Any


def _codex_item_id(tool_call_id: str) -> str:
    """Codex erwartet `fc_…`-IDs für Item-IDs. Anthropic gibt `toolu_…`."""
    if tool_call_id.startswith("fc_"):
        return tool_call_id
    if tool_call_id.startswith("call_"):
        return "fc_" + tool_call_id[len("call_"):]
    if tool_call_id:
        return "fc_" + tool_call_id.replace(" ", "_")
    return "fc_unknown"


def tools_to_codex(tools: list[dict]) -> list[dict]:
    """Anthropic-Tool-Schema → Responses-API-Function-Schema (flach, kein wrapper)."""
    out = []
    for t in tools or []:
        out.append({
            "type": "function",
            "name": t.get("name", ""),
            "description": t.get("description", "") or "",
            "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
            "strict": None,
        })
    return out


def messages_to_codex(messages: list[dict], system_prompt: str = "") -> tuple[str, list[dict]]:
    """Anthropic-messages → (instructions, input_items).

    instructions: System-Prompt-String.
    input_items: list mit role-Messages und top-level function_call/function_call_output-Items.
    """
    items: list[dict] = []

    for m in messages:
        role = m.get("role", "")
        content = m.get("content")

        if role == "user" and isinstance(content, str):
            items.append({"role": "user",
                          "content": [{"type": "input_text", "text": content}]})
            continue

        if role == "user" and isinstance(content, list):
            text_parts: list[str] = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                btype = b.get("type")
                if btype == "tool_result":
                    tc_id = b.get("tool_use_id", "")
                    inner = b.get("content")
                    if isinstance(inner, list):
                        text = "".join(x.get("text", "") for x in inner
                                       if isinstance(x, dict) and x.get("type") == "text")
                    else:
                        text = inner if isinstance(inner, str) else json.dumps(inner)
                    items.append({
                        "type": "function_call_output",
                        "call_id": tc_id,
                        "output": text or "",
                    })
                elif btype == "text":
                    text_parts.append(b.get("text", ""))
            if text_parts:
                items.append({"role": "user",
                              "content": [{"type": "input_text", "text": "".join(text_parts)}]})
            continue

        if role == "assistant" and isinstance(content, list):
            text_parts = []
            tool_uses: list[dict] = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                btype = b.get("type")
                if btype == "text":
                    text_parts.append(b.get("text", ""))
                elif btype == "tool_use":
                    tool_uses.append(b)
            joined = "".join(text_parts)
            if joined:
                items.append({"role": "assistant",
                              "content": [{"type": "output_text", "text": joined}]})
            for tu in tool_uses:
                tc_id = tu.get("id", "")
                items.append({
                    "type": "function_call",
                    "id": _codex_item_id(tc_id),
                    "call_id": tc_id,
                    "name": tu.get("name", ""),
                    "arguments": json.dumps(tu.get("input") or {}),
                })
            continue

        if role == "assistant" and isinstance(content, str):
            items.append({"role": "assistant",
                          "content": [{"type": "output_text", "text": content}]})

    return system_prompt or "", items


def codex_stop_to_anthropic(reason: str, has_tool_use: bool) -> str:
    """Responses-API stop reasons → Anthropic stop_reason."""
    if has_tool_use:
        return "tool_use"
    if reason in ("max_output_tokens", "length"):
        return "max_tokens"
    return "end_turn"
