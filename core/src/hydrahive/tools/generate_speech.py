"""Text-to-Speech über OpenRouter (gpt-audio, gestreamtes chat/completions).

Live verifiziert 2026-05-31 (3.23): gpt-audio erfordert `stream:true` +
`audio:{voice, format:"pcm16"}`. mp3 wird beim Streaming abgelehnt (anders als
Lyria). Das Audio kommt als raw PCM16 (24kHz mono 16-bit) gestreamt in
`delta.audio.data` — wird in einen WAV-Container gewrappt und im Agent-Workspace
gespeichert (von /api/files ausgeliefert), nur der Pfad geht ins LLM zurück.

Modell zentral aus media_models.tts (Default openai/gpt-audio).
"""
from __future__ import annotations

import base64
import binascii
import io
import logging
import wave

import httpx

from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_media import openrouter_key, read_audio_sse, save_bytes
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 120.0
_DEFAULT_VOICE = "alloy"
_SAMPLE_RATE = 24000  # OpenAI gpt-audio pcm16: 24kHz mono 16-bit

_DESCRIPTION = (
    "Wandelt Text in gesprochene Sprache über OpenRouter (gpt-audio). "
    "Die Audiodatei wird gespeichert und im Chat als Player angezeigt. "
    "Stimmen u.a.: alloy (default), echo, fable, onyx, nova, shimmer. "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "Der zu sprechende Text.",
        },
        "voice": {
            "type": "string",
            "description": "Stimme (alloy, echo, fable, onyx, nova, shimmer). Default alloy.",
            "default": _DEFAULT_VOICE,
        },
        "model": {
            "type": "string",
            "description": "OpenRouter-Modell. Default: zentrale media_models.tts (openai/gpt-audio).",
        },
    },
    "required": ["text"],
}


def _pcm16_to_wav(pcm: bytes, sample_rate: int = _SAMPLE_RATE) -> bytes:
    """Wrappt raw PCM16 (mono, 16-bit) in einen WAV-Container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


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
    voice = (args.get("voice") or _DEFAULT_VOICE).strip()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "modalities": ["text", "audio"],
        "audio": {"voice": voice, "format": "pcm16"},
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
                    logger.warning("generate_speech HTTP %s: %s", resp.status_code, body)
                    return ToolResult.fail(f"OpenRouter API-Fehler {resp.status_code}: {body}")
                b64_parts, done = await read_audio_sse(resp)
    except httpx.HTTPError as e:
        logger.warning("generate_speech Netzwerk-Fehler: %s", e)
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
            "Keine Audio-Daten in OpenRouter-Antwort — bitte erneut versuchen"
        )

    try:
        pcm = base64.b64decode("".join(b64_parts), validate=True)
    except (ValueError, binascii.Error) as e:
        return ToolResult.fail(f"Audio-Daten ungültig (base64 nicht dekodierbar): {e}")

    wav = _pcm16_to_wav(pcm)
    path = save_bytes(wav, ctx.workspace / "generated", "wav")
    logger.info("generate_speech: gespeichert model=%s voice=%s path=%s bytes=%d",
                model, voice, path, len(wav))
    return ToolResult.ok(f"Sprache generiert und gespeichert: {path}", model=model, voice=voice)


TOOL = Tool(
    name="generate_speech",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
