"""OpenAI Codex Backend-Provider — chatgpt.com/backend-api/codex/responses.

Codex erfordert stream=true; codex_call ist Wrapper über codex_stream.
codex_stream yieldet HH2-normalisierte Events (kompatibel zu anthropic_stream).
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from hydrahive.runner._codex_convert import (
    codex_stop_to_anthropic,
    messages_to_codex,
    tools_to_codex,
)

logger = logging.getLogger(__name__)

CODEX_URL = "https://chatgpt.com/backend-api/codex/responses"
_TIMEOUT = 300.0


_DEFAULT_INSTRUCTIONS = "You are a helpful assistant."


def _build_payload(
    *, model: str, system_prompt: str, messages: list[dict], tools: list[dict],
) -> dict:
    instructions, input_items = messages_to_codex(messages, system_prompt)
    payload: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "store": False,
        "stream": True,
        "text": {"verbosity": "medium"},
        "include": ["reasoning.encrypted_content"],
        "parallel_tool_calls": True,
        "instructions": instructions or _DEFAULT_INSTRUCTIONS,
    }
    codex_tools = tools_to_codex(tools)
    if codex_tools:
        payload["tools"] = codex_tools
        payload["tool_choice"] = "auto"
    return payload


def _headers(*, access_token: str, account_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "OpenAI-Beta": "responses=experimental",
        "originator": "hydrahive",
        "Content-Type": "application/json",
    }


def _parse_sse_line(line: str) -> dict | None:
    if not line.startswith("data: "):
        return None
    body = line[6:].strip()
    if not body or body == "[DONE]":
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


async def codex_stream(
    *, access_token: str, account_id: str, model: str,
    system_prompt: str, messages: list[dict], tools: list[dict],
) -> AsyncIterator[dict]:
    """HH2-normalisierte Stream-Events aus Codex."""
    payload = _build_payload(
        model=model, system_prompt=system_prompt, messages=messages, tools=tools,
    )
    text_index: int | None = None
    fn_index: dict[str, int] = {}
    next_index = 0
    accumulated_fn: dict[str, dict] = {}
    fn_order: list[str] = []
    text_buf = ""
    usage_in = usage_out = cache_read = 0

    yield {"type": "message_start"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        async with client.stream(
            "POST", CODEX_URL,
            headers=_headers(access_token=access_token, account_id=account_id),
            json=payload,
        ) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode(errors="replace")[:500]
                raise RuntimeError(f"Codex API {resp.status_code}: {body}")

            async for line in resp.aiter_lines():
                ev = _parse_sse_line(line)
                if ev is None:
                    continue
                t = ev.get("type", "")

                if t == "response.output_text.delta":
                    delta = ev.get("delta", "")
                    if not delta:
                        continue
                    if text_index is None:
                        text_index = next_index
                        next_index += 1
                        yield {"type": "block_start", "index": text_index,
                               "block_type": "text"}
                    text_buf += delta
                    yield {"type": "text_delta", "index": text_index, "text": delta}

                elif t == "response.output_item.added":
                    item = ev.get("item", {}) or {}
                    if item.get("type") != "function_call":
                        continue
                    item_id = item.get("id", "")
                    call_id = item.get("call_id", "") or item_id
                    name = item.get("name", "")
                    accumulated_fn[item_id] = {
                        "id": item_id, "call_id": call_id, "name": name, "arguments": "",
                    }
                    fn_order.append(item_id)
                    idx = next_index
                    next_index += 1
                    fn_index[item_id] = idx
                    yield {"type": "block_start", "index": idx, "block_type": "tool_use",
                           "id": call_id, "name": name}

                elif t == "response.function_call_arguments.delta":
                    item_id = ev.get("item_id") or ev.get("call_id", "")
                    if item_id not in accumulated_fn:
                        continue
                    delta = ev.get("delta", "")
                    accumulated_fn[item_id]["arguments"] += delta
                    yield {"type": "input_delta", "index": fn_index[item_id],
                           "json_partial": delta}

                elif t == "response.function_call_arguments.done":
                    item_id = ev.get("item_id") or ev.get("call_id", "")
                    if item_id in accumulated_fn:
                        final_args = ev.get(
                            "arguments", accumulated_fn[item_id]["arguments"])
                        accumulated_fn[item_id]["arguments"] = final_args
                        yield {"type": "block_stop", "index": fn_index[item_id]}

                elif t == "response.completed":
                    usage = (ev.get("response", {}) or {}).get("usage", {}) or {}
                    usage_in = int(usage.get("input_tokens") or 0)
                    usage_out = int(usage.get("output_tokens") or 0)
                    details = usage.get("input_tokens_details") or {}
                    cache_read = int(details.get("cached_tokens") or 0)

    if text_index is not None:
        yield {"type": "block_stop", "index": text_index}

    blocks: list[dict] = []
    if text_buf:
        blocks.append({"type": "text", "text": text_buf})
    for fn_id in fn_order:
        fn = accumulated_fn[fn_id]
        try:
            args = json.loads(fn.get("arguments", "") or "{}")
        except json.JSONDecodeError:
            args = {"_raw_arguments": fn.get("arguments", "")}
        blocks.append({
            "type": "tool_use",
            "id": fn.get("call_id", "") or fn_id,
            "name": fn.get("name", ""),
            "input": args,
        })

    yield {
        "type": "message_stop",
        "stop_reason": codex_stop_to_anthropic("", bool(fn_order)),
        "blocks": blocks,
        "input_tokens": usage_in,
        "output_tokens": usage_out,
        "cache_creation_tokens": 0,
        "cache_read_tokens": cache_read,
    }


async def codex_call(
    *, access_token: str, account_id: str, model: str,
    system_prompt: str, messages: list[dict], tools: list[dict],
) -> tuple[list[dict], str]:
    """Non-streaming Wrapper. Verbraucht codex_stream und gibt das finale
    message_stop-Event als (blocks, stop_reason) zurück."""
    final: dict | None = None
    async for ev in codex_stream(
        access_token=access_token, account_id=account_id, model=model,
        system_prompt=system_prompt, messages=messages, tools=tools,
    ):
        if ev.get("type") == "message_stop":
            final = ev
    if not final:
        raise RuntimeError("Codex-Stream ohne message_stop beendet")
    return final.get("blocks", []), final.get("stop_reason", "end_turn")
