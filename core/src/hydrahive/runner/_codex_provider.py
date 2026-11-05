"""OpenAI Codex Backend-Provider — chatgpt.com/backend-api/codex/responses.

Codex erfordert stream=true; codex_call ist Wrapper über codex_stream.
codex_stream yieldet HH2-normalisierte Events (kompatibel zu anthropic_stream).
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator

import httpx

from hydrahive.runner._codex_convert import codex_stop_to_anthropic
from hydrahive.runner._codex_http import (  # noqa: F401 — Re-Export für Aufrufer/Tests
    CODEX_URL,
    CodexModelNotAllowed,
    CodexStreamError,
    CodexStreamStall,
    _build_payload,
    _headers,
    _parse_sse_line,
    _stream_error_text,
)

logger = logging.getLogger(__name__)

_TIMEOUT = 300.0
# Fristen gegen stehende Verbindungen (Befund hydratest 5.11.2026: 2 von 12 Anfragen blieben ohne Daten stehen und
# warteten das volle 300-s-Lesezeitlimit ab). Normal: erstes Ereignis ~1 s, größte Lücke bei reasoning_effort=high 4,3 s.
# Die Fristen gelten je Leseschritt, nicht für die Gesamtdauer – wer stetig liefert, wird nie abgebrochen.
_FIRST_EVENT_TIMEOUT = 30.0
_GAP_TIMEOUT = 90.0


@asynccontextmanager
async def _open_stream(client: httpx.AsyncClient, **kwargs) -> AsyncIterator[httpx.Response]:
    """`client.stream(...)` mit Frist bis zum Antwortkopf. Gemessen (hydratest 5.11., 30 echte Anfragen): 4 von 5
    Aussetzern standen VOR dem Kopf – dort greift keine Zeilenfrist. Gilt die erste Frist; Abbruch von außen läuft
    unverändert durch. `AsyncExitStack` räumt die Antwort in jedem Fall auf (Normalende, Fehler, Abbruch)."""
    async with AsyncExitStack() as stack:
        try:
            resp = await asyncio.wait_for(stack.enter_async_context(client.stream("POST", **kwargs)), _FIRST_EVENT_TIMEOUT)
        except asyncio.TimeoutError:
            raise CodexStreamStall(
                f"Codex-Stream steht: Antwortkopf nach {_FIRST_EVENT_TIMEOUT:g} s noch nicht da") from None
        yield resp


async def _timed_lines(resp: httpx.Response) -> AsyncIterator[str]:
    """Zeilen der Antwort mit Frist je Leseschritt. Frist verstrichen → CodexStreamStall; ein Abbruch von außen
    (CancelledError) läuft unverändert durch."""
    it = resp.aiter_lines().__aiter__()
    first = True
    while True:
        limit = _FIRST_EVENT_TIMEOUT if first else _GAP_TIMEOUT
        try:
            line = await asyncio.wait_for(it.__anext__(), limit)
        except StopAsyncIteration:
            return
        except asyncio.TimeoutError:
            what = "erstes Ereignis" if first else "Pause zwischen Ereignissen"
            raise CodexStreamStall(f"Codex-Stream steht: {what} nach {limit:g} s noch nicht da") from None
        if line.strip():
            first = False
        yield line


async def codex_stream(
    *, access_token: str, account_id: str, model: str,
    system_prompt: str, messages: list[dict], tools: list[dict],
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
) -> AsyncIterator[dict]:
    """HH2-normalisierte Stream-Events aus Codex."""
    payload = _build_payload(
        model=model, system_prompt=system_prompt, messages=messages, tools=tools,
        reasoning_effort=reasoning_effort, max_tokens=max_tokens,
    )
    text_index: int | None = None
    fn_index: dict[str, int] = {}
    next_index = 0
    accumulated_fn: dict[str, dict] = {}
    fn_order: list[str] = []
    text_buf = ""
    usage_in = usage_out = cache_read = 0
    reasoning_items: list[dict] = []
    completed = False

    yield {"type": "message_start"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        async with _open_stream(
            client, url=CODEX_URL,
            headers=_headers(access_token=access_token, account_id=account_id),
            json=payload,
        ) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode(errors="replace")[:500]
                if resp.status_code == 400 and "not supported" in body and "ChatGPT account" in body:
                    raise CodexModelNotAllowed(
                        f"Modell '{model}' ist mit deinem ChatGPT-Account nicht "
                        f"verfügbar (vermutlich brauchst du ChatGPT Pro). "
                        f"Wähle ein anderes Codex-Modell — gpt-5.2, gpt-5.4 oder gpt-5.5."
                    )
                raise RuntimeError(f"Codex API {resp.status_code}: {body}")

            async for line in _timed_lines(resp):
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

                elif t in ("response.output_item.added", "response.output_item.done"):
                    item = ev.get("item", {}) or {}
                    if item.get("type") == "reasoning":
                        encrypted = item.get("encrypted_content")
                        if encrypted and not any(
                            block.get("encrypted_content") == encrypted for block in reasoning_items
                        ):
                            reasoning_items.append({
                                "type": "codex_reasoning", "encrypted_content": encrypted,
                                "model": f"openai-codex/{model}",
                            })
                        continue
                    # Function calls are initialized on added; done would duplicate them.
                    if t != "response.output_item.added" or item.get("type") != "function_call":
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

                elif t in ("error", "response.failed", "response.incomplete"):
                    # Früher stillschweigend ignoriert: Der Lauf endete mit 0 Blöcken
                    # und der Nutzer sah nur "leere Antwort" (Befund VPS 04.10.2026).
                    raise CodexStreamError(_stream_error_text(t, ev))

                elif t == "response.completed":
                    completed = True
                    usage = (ev.get("response", {}) or {}).get("usage", {}) or {}
                    usage_in = int(usage.get("input_tokens") or 0)
                    usage_out = int(usage.get("output_tokens") or 0)
                    details = usage.get("input_tokens_details") or {}
                    cache_read = int(details.get("cached_tokens") or 0)

    if not completed:
        # Stream ohne response.completed: Verbindung abgebrochen oder Server hat
        # den Lauf verworfen. Lieber klar scheitern als eine leere Antwort liefern.
        raise CodexStreamError("Codex-Stream ohne Abschluss beendet (Verbindung abgebrochen?)")

    if text_index is not None:
        yield {"type": "block_stop", "index": text_index}

    blocks: list[dict] = list(reasoning_items)
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
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
) -> tuple[list[dict], str, dict[str, int]]:
    """Non-streaming Wrapper. Verbraucht codex_stream und gibt das finale
    message_stop-Event als (blocks, stop_reason, usage) zurück."""
    final: dict | None = None
    async for ev in codex_stream(
        access_token=access_token, account_id=account_id, model=model,
        system_prompt=system_prompt, messages=messages, tools=tools,
        reasoning_effort=reasoning_effort, max_tokens=max_tokens,
    ):
        if ev.get("type") == "message_stop":
            final = ev
    if not final:
        raise RuntimeError("Codex-Stream ohne message_stop beendet")
    usage = {
        "input_tokens": final.get("input_tokens", 0),
        "output_tokens": final.get("output_tokens", 0),
        "cache_creation_tokens": final.get("cache_creation_tokens", 0),
        "cache_read_tokens": final.get("cache_read_tokens", 0),
    }
    return final.get("blocks", []), final.get("stop_reason", "end_turn"), usage
