"""Text-to-Speech über OpenRouter (dünner Wrapper um synthesize_speech).

Die eigentliche Synthese (POST /audio/speech, Voice-Auflösung, pcm→WAV) liegt
in `_openrouter_media.synthesize_speech` — geteilt mit dem Vorlese-TTS-Pfad
(voice/tts.py). gpt-audio über chat/completions war der falsche Weg (Chat-Modell,
antwortet statt vorzulesen). Modell zentral aus media_models.tts.
"""
from __future__ import annotations

import logging

from hydrahive.llm._config import openrouter_key
from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_media import save_bytes, synthesize_speech
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

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
