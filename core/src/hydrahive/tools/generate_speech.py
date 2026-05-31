"""Text-to-Speech über OpenRouter — dedizierter /audio/speech-Endpoint.

Live verifiziert 2026-05-31 (3.23): POST /api/v1/audio/speech mit
{model, input, voice, response_format:"pcm"} liefert rohe PCM16-Bytes — verbatim,
kein Streaming, kein Konversations-Modell. (gpt-audio über chat/completions war
der falsche Weg: das ist ein Chat-Modell und *antwortet* auf den Text.)

`pcm` ist universell (Gemini-TTS will NUR pcm, andere können's auch). Die
Sample-Rate steht im content-type-Header (audio/pcm;rate=24000;channels=1) →
zuverlässig zu WAV gewrappt. Liefert ein Modell doch mp3, wird es direkt
gespeichert.

Speech-Modelle haben Modalität output:["speech"] und liegen NICHT im chat-/models
— eigene Fläche (media_models.list_speech_models). voice ist Pflicht; ohne
Angabe wird die erste supported_voice des Modells genommen.

Modell zentral aus media_models.tts (Default hexgrad/kokoro-82m).
"""
from __future__ import annotations

import logging

import httpx

from hydrahive.llm.media_models import first_voice, get_media_model
from hydrahive.llm._config import openrouter_key
from hydrahive.tools._openrouter_media import parse_pcm_content_type, pcm16_to_wav, save_bytes
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/audio/speech"
_TIMEOUT = 120.0

_DESCRIPTION = (
    "Wandelt Text in gesprochene Sprache über OpenRouter (echtes TTS, verbatim). "
    "Die Audiodatei wird gespeichert und im Chat als Player angezeigt. "
    "Stimmen je Modell verschieden — ohne Angabe wird die Standard-Stimme genutzt. "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "Der zu sprechende Text (wird wortwörtlich vorgelesen).",
        },
        "voice": {
            "type": "string",
            "description": "Stimme (modellabhängig). Ohne Angabe: Standard-Stimme des Modells.",
        },
        "model": {
            "type": "string",
            "description": "OpenRouter-Speech-Modell. Default: zentrale media_models.tts.",
        },
    },
    "required": ["text"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    text = (args.get("text") or "").strip()
    if not text:
        return ToolResult.fail("Text darf nicht leer sein")

    key = openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    model = (args.get("model") or get_media_model("tts")).strip()
    voice = (args.get("voice") or "").strip() or await first_voice(model)
    if not voice:
        return ToolResult.fail(
            f"Keine Voice angegeben und keine Standard-Stimme für '{model}' gefunden — "
            "voice setzen (siehe Modell-Voices)"
        )

    # pcm = universell (auch Gemini), Rate kommt aus dem content-type-Header.
    payload = {"model": model, "input": text, "voice": voice, "response_format": "pcm"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _OPENROUTER_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                body = resp.text[:400]
                logger.warning("generate_speech HTTP %s: %s", resp.status_code, body)
                return ToolResult.fail(f"OpenRouter API-Fehler {resp.status_code}: {body}")
            raw = resp.content
            content_type = resp.headers.get("content-type", "")
    except httpx.HTTPError as e:
        logger.warning("generate_speech Netzwerk-Fehler: %s", e)
        return ToolResult.fail(f"Netzwerk-Fehler: {e}")

    if not raw:
        return ToolResult.fail("Keine Audio-Daten in OpenRouter-Antwort — bitte erneut versuchen")

    if "mpeg" in content_type or "mp3" in content_type:
        data, ext = raw, "mp3"
    else:
        rate, channels = parse_pcm_content_type(content_type)
        data, ext = pcm16_to_wav(raw, sample_rate=rate, channels=channels), "wav"

    path = save_bytes(data, ctx.workspace / "generated", ext)
    logger.info("generate_speech: gespeichert model=%s voice=%s ct=%s path=%s bytes=%d",
                model, voice, content_type, path, len(data))
    return ToolResult.ok(f"Sprache generiert und gespeichert: {path}", model=model, voice=voice)


TOOL = Tool(
    name="generate_speech",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
