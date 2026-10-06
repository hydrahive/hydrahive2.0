"""Anthropic-SDK-Aufrufe für llm.client complete()/stream() (Claude direkt + MiniMax).

role=system-Nachrichten werden als top-level ``system`` übergeben (Anthropic erlaubt sie
nicht in ``messages``). Bei OAuth steht davor die Claude-Code-Identity – ERGÄNZT, nicht
ersetzt (Bug bis 06.10.2026: die Anweisung des Aufrufers ging verloren).
"""
from __future__ import annotations

from typing import AsyncIterator

from hydrahive.llm._anthropic import (
    MINIMAX_BASE_URL,
    _OAUTH_HEADERS,
    _OAUTH_IDENTITY,
    extract_text,
    strip_provider_prefix,
)


def split_system(messages: list[dict]) -> tuple[str, list[dict]]:
    """(Systemtext, übrige Nachrichten). Mehrere system-Nachrichten werden in Reihenfolge verbunden;
    Inhalt darf String oder Liste von Text-Blöcken sein."""
    texts: list[str] = []
    rest: list[dict] = []
    for m in messages:
        if m.get("role") != "system":
            rest.append(m)
            continue
        c = m.get("content")
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, list):
            texts.append("".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"))
    return "\n\n".join(t for t in texts if t), rest


def _system_param(system_text: str, is_oauth: bool) -> str | list | None:
    """OAuth verlangt die Identity als ersten System-Block; die Anweisung kommt als eigener Block dahinter."""
    if is_oauth:
        blocks = [dict(b) for b in _OAUTH_IDENTITY]
        if system_text:
            blocks.append({"type": "text", "text": system_text})
        return blocks
    return system_text or None


def _client(key: str):
    """Anthropic-SDK-Client. OAuth-Tokens brauchen auth_token + Identity-Header,
    Plain-API-Keys brauchen api_key. Beide gehen über das gleiche SDK."""
    import anthropic as _anthropic
    if key.startswith("sk-ant-oat"):
        return _anthropic.AsyncAnthropic(
            api_key="", auth_token=key, timeout=300.0,
            default_headers=_OAUTH_HEADERS,
        ), True
    return _anthropic.AsyncAnthropic(api_key=key, timeout=300.0), False


def _is_temperature_deprecated_error(exc: Exception) -> bool:
    """True wenn Anthropic mit 'temperature is deprecated for this model' 400t.

    Manche neueren Claude-Modelle (z.B. opus-4-7+, sonnet-5) akzeptieren keinen
    temperature-Parameter mehr. Gilt für alle direkten Anthropic-SDK-Pfade
    (complete/stream, OAuth/API-Key/MiniMax) — nicht nur den Runner-Pfad.
    """
    msg = str(exc).lower()
    return "temperature" in msg and "deprecated" in msg


async def anthropic_complete(
    key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> str:
    client, is_oauth = _client(key)
    system_text, user_messages = split_system(messages)
    system = _system_param(system_text, is_oauth)
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": user_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system
    from hydrahive.llm._oauth_usage import extract_rate_limit_headers
    import anthropic as _anthropic

    try:
        raw_resp = await client.messages.with_raw_response.create(**kwargs)
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        raw_resp = await client.messages.with_raw_response.create(**kwargs)
    extract_rate_limit_headers(raw_resp.headers)
    resp = raw_resp.parse()
    return extract_text(resp.content)


async def minimax_complete(
    api_key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> str:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=60.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    system_text, rest = split_system(messages)
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": rest,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_text:
        kwargs["system"] = system_text
    try:
        resp = await client.messages.create(**kwargs)
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        resp = await client.messages.create(**kwargs)
    return extract_text(resp.content)


async def minimax_stream(
    api_key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> AsyncIterator[str]:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=60.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    system_text, rest = split_system(messages)
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": rest,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_text:
        kwargs["system"] = system_text
    try:
        async with client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield text
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        async with client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield text


async def anthropic_stream(
    key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> AsyncIterator[str]:
    import anthropic as _anthropic

    client, is_oauth = _client(key)
    system_text, user_messages = split_system(messages)
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": user_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    system = _system_param(system_text, is_oauth)
    if system:
        kwargs["system"] = system
    try:
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
