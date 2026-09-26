"""Text-to-Speech über OpenRouter (dünner Wrapper um synthesize_speech).

Die eigentliche Synthese (POST /audio/speech, Voice-Auflösung, pcm→WAV) liegt
in `_openrouter_media.synthesize_speech` — geteilt mit dem Vorlese-TTS-Pfad
(voice/tts.py). gpt-audio über chat/completions war der falsche Weg (Chat-Modell,
antwortet statt vorzulesen). Modell zentral aus media_models.tts.
"""
from __future__ import annotations

import logging

from hydrahive.llm._config import openrouter_key
from hydrahive.llm.local_voice import is_local
from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_media import save_bytes, synthesize_speech
from hydrahive.tools.base import Tool, ToolContext, ToolResult
from hydrahive.voice.tts import synthesize_local

logger = logging.getLogger(__name__)

_DESCRIPTION = (
    "Wandelt Text in gesprochene Sprache (echtes TTS, verbatim). "
    "Die Audiodatei wird gespeichert und im Chat als Player angezeigt. "
    "Stimmen je Modell verschieden — ohne Angabe wird die Standard-Stimme genutzt. "
    "Modell 'local/piper' nutzt den lokalen Piper auf diesem Server (kein Cloud-Key, eine feste "
    "deutsche Stimme); OpenRouter-Modelle brauchen einen OpenRouter API-Key."
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
            "description": (
                "Speech-Modell. Default: zentrale media_models.tts. "
                "'local/piper' = lokaler Piper auf diesem Server; sonst OpenRouter-Speech-Modell."
            ),
        },
    },
    "required": ["text"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    text = (args.get("text") or "").strip()
    if not text:
        return ToolResult.fail("Text darf nicht leer sein")

    model = (args.get("model") or get_media_model("tts")).strip()

    # Lokaler Piper (TTS-Container) — kein Cloud-Key nötig, eine feste Stimme.
    if is_local(model):
        try:
            data, _mime = await synthesize_local(text, args.get("voice") or "")
        except (RuntimeError, OSError) as e:
            return ToolResult.fail(f"Lokale Sprachausgabe fehlgeschlagen: {e}")
        path = save_bytes(data, ctx.workspace / "generated", "wav")
        logger.info("generate_speech: gespeichert model=%s path=%s bytes=%d", model, path, len(data))
        return ToolResult.ok(f"Sprache generiert und gespeichert: {path}", model=model, voice="")

    key = openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    try:
        data, ext, voice, note = await synthesize_speech(
            text, args.get("voice") or "", model, key=key
        )
    except RuntimeError as e:
        return ToolResult.fail(str(e))

    path = save_bytes(data, ctx.workspace / "generated", ext)
    logger.info("generate_speech: gespeichert model=%s voice=%s path=%s bytes=%d",
                model, voice, path, len(data))
    msg = f"Sprache generiert und gespeichert: {path}"
    if note:
        msg += f" ({note})"
    return ToolResult.ok(msg, model=model, voice=voice)


TOOL = Tool(
    name="generate_speech",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
