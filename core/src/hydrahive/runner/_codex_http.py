"""Codex-HTTP-Hilfen: Payload, Header, SSE-Parser, Fehler.

Ausgelagert aus _codex_provider.py (Dateigrößen-Regel). Der Provider
importiert alles von hier und re-exportiert die öffentlichen Namen.
"""
from __future__ import annotations

import json
from typing import Any

from hydrahive.runner._codex_convert import messages_to_codex, tools_to_codex

CODEX_URL = "https://chatgpt.com/backend-api/codex/responses"


class CodexModelNotAllowed(Exception):
    """Codex hat das Modell mit 'not supported when using Codex with a ChatGPT account'
    abgelehnt. Bedeutet: ChatGPT-Plus-Account hat keinen Zugriff auf dieses Modell
    (z.B. -codex-Suffix-Varianten erfordern oft ChatGPT-Pro). Tipp an User: anderes
    Modell wählen — gpt-5.2, gpt-5.4, gpt-5.5 funktionieren bei den meisten Accounts."""


_DEFAULT_INSTRUCTIONS = "You are a helpful assistant."


class CodexStreamError(RuntimeError):
    """Codex meldet im Stream einen Fehler oder bricht ohne Abschluss ab."""


def _stream_error_text(event_type: str, ev: dict) -> str:
    resp = ev.get("response") or {}
    err = ev.get("error") or resp.get("error") or {}
    if isinstance(err, dict):
        msg = err.get("message") or err.get("code") or ""
        code = err.get("code") or err.get("type") or ""
    else:
        msg, code = str(err), ""
    if not msg and event_type == "response.incomplete":
        reason = (resp.get("incomplete_details") or {}).get("reason") or "unbekannt"
        msg = f"Antwort unvollständig ({reason})"
    if not msg:
        msg = ev.get("message") or "ohne Details"
    return f"Codex-Fehler ({code or event_type}): {msg}"[:500]

def _build_payload(
    *, model: str, system_prompt: str, messages: list[dict], tools: list[dict],
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
) -> dict:
    instructions, input_items = messages_to_codex(
        messages, system_prompt, model=f"openai-codex/{model}",
    )
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
    # Der Codex-OAuth-/Responses-Backend lehnt max_output_tokens ab
    # ("Unsupported parameter"). Der offizielle Codex-Client sendet es nicht;
    # das Output-Limit wird serverseitig gesteuert. max_tokens bleibt in der
    # Signatur für API-Parität, wird für diesen Pfad aber nicht übertragen.
    _ = max_tokens
    if reasoning_effort:
        from hydrahive.llm.reasoning_effort import effort_levels_for_model
        if reasoning_effort in effort_levels_for_model(f"openai-codex/{model}"):
            payload["reasoning"] = {"effort": reasoning_effort}
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
