"""Musikgenerierung über OpenRouter (Lyria 3, synchron via gestreamtes chat/completions).

Format abgeglichen mit der kanonischen OpenClaw-Implementierung (PR #82789,
gemergt 2026-05-17) und live verifiziert auf 3.23:

  Pflicht-Parameter für Audio-Output:
    modalities: ["text", "audio"]
    audio:      {"format": "mp3"}   ← ohne das liefert Lyria nicht-deterministisch
                                       mal Audio, mal nur Struktur-Marker
    stream:     true

Das Audio kommt gestreamt in `delta.audio.data` (base64) — der eigentliche
Chunk ist EINE mehrere MB große SSE-Zeile. Deshalb wird über rohe Bytes
gepuffert und selbst an Zeilen getrennt; httpx' aiter_lines() zerlegt diese
Riesenzeile nicht-deterministisch. Der Stream gilt erst mit `[DONE]` als
vollständig — sonst war es ein Abbruch, kein leeres Ergebnis.

Modelle:
  google/lyria-3-pro-preview   — vollständige Stücke (default)
  google/lyria-3-clip-preview  — kurze Clips
"""
from __future__ import annotations

import base64
import binascii
import logging

import httpx

from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_media import (
    audio_chunk_from_sse_line as _audio_chunk_from_sse_line,
    is_done_line as _is_done_line,
    openrouter_key,
    read_audio_sse,
    save_bytes,
)
from hydrahive.tools.base import Tool, ToolContext, ToolResult

# Re-Export für Rückwärtskompatibilität (Tests referenzieren diese Namen).
__all__ = ["TOOL", "_audio_chunk_from_sse_line", "_is_done_line"]

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


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return ToolResult.fail("Prompt darf nicht leer sein")

    key = openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    model = (args.get("model") or get_media_model("music")).strip()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["text", "audio"],
        "audio": {"format": "mp3"},
        "stream": True,
    }

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
                b64_parts, done = await read_audio_sse(resp)
    except httpx.HTTPError as e:
        logger.warning("generate_music Netzwerk-Fehler: %s", e)
        return ToolResult.fail(f"Netzwerk-Fehler: {e}")

    if not done and not b64_parts:
        return ToolResult.fail(
            "OpenRouter-Stream vorzeitig beendet (kein [DONE]) — keine Daten erhalten"
        )
    if b64_parts and not done:
        return ToolResult.fail(
            "OpenRouter-Stream vorzeitig beendet (kein [DONE]) — Audio unvollständig, bitte erneut versuchen"
        )
    if not b64_parts:
        return ToolResult.fail(
            "Keine Audio-Daten in OpenRouter-Antwort (Provider lieferte nur Struktur, keinen Track) "
            "— bitte erneut versuchen"
        )

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
