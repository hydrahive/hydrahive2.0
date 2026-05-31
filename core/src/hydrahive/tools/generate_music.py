"""Musikgenerierung über OpenRouter (Lyria 3, synchron via gestreamtes chat/completions).

Live verifiziert 2026-05-31 (3.23): Audio-Output erfordert `stream:true` +
`modalities:["audio","text"]`. Das Audio kommt gestreamt in `delta.audio.data`
(base64, ggf. mehrere Chunks), Default-Format MP3. Wird im Agent-Workspace
gespeichert (von /api/files ausgeliefert), nur der Pfad geht ins LLM zurück.

Modelle:
  google/lyria-3-pro-preview   — vollständige Stücke (default)
  google/lyria-3-clip-preview  — kurze Clips
"""
from __future__ import annotations

import base64
import binascii
import json
import logging

import httpx

from hydrahive.tools._openrouter_media import openrouter_key, save_bytes
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "google/lyria-3-pro-preview"
_TIMEOUT = 180.0

_DESCRIPTION = (
    "Generiert Musik aus einem Text-Prompt über OpenRouter (Lyria 3). "
    "Das Stück wird gespeichert und im Chat als Audio-Player angezeigt. "
    "Modelle: google/lyria-3-pro-preview (default, ganze Stücke), "
    "google/lyria-3-clip-preview (kurze Clips). "
    "Prompt auf Englisch, Genre/Stimmung/Instrumente beschreiben. "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "Musikbeschreibung auf Englisch (Genre, Stimmung, Instrumente, Tempo).",
        },
        "model": {
            "type": "string",
            "description": "OpenRouter-Modell. Default: google/lyria-3-pro-preview. Kurz: google/lyria-3-clip-preview",
            "default": _DEFAULT_MODEL,
        },
    },
    "required": ["prompt"],
}


def _audio_chunk_from_sse_line(line: str) -> str | None:
    """Extrahiert delta.audio.data (base64) aus einer SSE-Zeile, sonst None."""
    if not line.startswith("data: "):
        return None
    payload = line[6:]
    if payload.strip() == "[DONE]":
        return None
    try:
        chunk = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        return None
    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
    audio = delta.get("audio")
    if isinstance(audio, dict):
        return audio.get("data")
    return None


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return ToolResult.fail("Prompt darf nicht leer sein")

    key = openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    model = (args.get("model") or _DEFAULT_MODEL).strip()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["audio", "text"],
        "stream": True,
    }

    b64_parts: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream(
                "POST", _OPENROUTER_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")[:400]
                    logger.warning("generate_music HTTP %s: %s", resp.status_code, body)
                    return ToolResult.fail(f"OpenRouter API-Fehler {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    chunk = _audio_chunk_from_sse_line(line)
                    if chunk:
                        b64_parts.append(chunk)
    except httpx.HTTPError as e:
        logger.warning("generate_music Netzwerk-Fehler: %s", e)
        return ToolResult.fail(f"Netzwerk-Fehler: {e}")

    if not b64_parts:
        return ToolResult.fail("Kein Audio in OpenRouter-Antwort erhalten")

    try:
        raw = base64.b64decode("".join(b64_parts), validate=True)
    except (ValueError, binascii.Error) as e:
        return ToolResult.fail(f"Audio-Daten ungültig (base64 nicht dekodierbar): {e}")

    path = save_bytes(raw, ctx.workspace / "generated", "mp3")
    logger.info("generate_music: gespeichert model=%s path=%s bytes=%d", model, path, len(raw))
    return ToolResult.ok(f"Musik generiert und gespeichert: {path}", model=model)


TOOL = Tool(
    name="generate_music",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
