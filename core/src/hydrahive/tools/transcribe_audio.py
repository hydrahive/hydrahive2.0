"""Audio-Transkriptions-Tool via OpenRouter Whisper-API (#151).

Agenten können damit Audio-Dateien (heruntergeladene Voice-Messages, Workspace-
Dateien usw.) transkribieren lassen. Die Mikrofon-Eingabe im Chat läuft
separat über den lokalen Wyoming-Container — diese Tool ist für Agenten-Use-Cases.

Unterstützte Formate: webm, mp4/m4a, mp3, ogg, wav, flac (alles was Whisper versteht).
Modell-Default aus `media_models["transcribe"]`, überschreibbar per Parameter.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_transcribe import openrouter_key, transcribe_file
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "openai/whisper-large-v3"
_MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB — Whisper-API-Limit

_DESCRIPTION = (
    "Transkribiert eine Audio-Datei (lokaler Pfad im Workspace) zu Text via OpenRouter Whisper. "
    "Nützlich für heruntergeladene Voice-Messages, Sprach-Notizen oder andere Audio-Dateien. "
    "Unterstützte Formate: mp3, mp4, m4a, webm, ogg, wav, flac. "
    "Gibt den transkribierten Text zurück. "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "file": {
            "type": "string",
            "description": "Absoluter Dateipfad zur Audio-Datei im Workspace.",
        },
        "language": {
            "type": "string",
            "description": (
                "Sprach-ISO-Code (z.B. 'de', 'en', 'fr'). "
                "Leer lassen für Auto-Detect (Standard, gut ab ~3s Audio)."
            ),
        },
        "model": {
            "type": "string",
            "description": (
                f"OpenRouter-Whisper-Modell. Default: {_DEFAULT_MODEL}. "
                "Weitere: openai/whisper-1, openai/whisper-large-v3-turbo"
            ),
        },
    },
    "required": ["file"],
}


def _mime_for(path: Path) -> str:
    """Ermittelt MIME-Type aus Dateiendung. Fallback: audio/mpeg."""
    mime = mimetypes.guess_type(path.name)[0] or ""
    if mime.startswith("audio/") or mime.startswith("video/"):
        return mime
    ext = path.suffix.lower()
    return {
        ".webm": "audio/webm", ".ogg": "audio/ogg",
        ".mp4": "video/mp4", ".m4a": "audio/mp4",
        ".wav": "audio/wav", ".flac": "audio/flac",
    }.get(ext, "audio/mpeg")


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    file_arg = (args.get("file") or "").strip()
    if not file_arg:
        return ToolResult.fail("'file' darf nicht leer sein")

    path = Path(file_arg)
    if not path.exists():
        return ToolResult.fail(f"Datei nicht gefunden: {file_arg}")
    if not path.is_file():
        return ToolResult.fail(f"Pfad ist kein File: {file_arg}")

    size = path.stat().st_size
    if size > _MAX_FILE_BYTES:
        mb = size / (1024 * 1024)
        return ToolResult.fail(
            f"Datei zu groß ({mb:.1f} MB) — Whisper-Limit ist {_MAX_FILE_BYTES // (1024*1024)} MB"
        )
    if size == 0:
        return ToolResult.fail("Leere Audio-Datei")

    key = openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    model = (args.get("model") or get_media_model("transcribe") or _DEFAULT_MODEL).strip()
    language = (args.get("language") or "").strip() or None

    filename = f"{path.stem}{path.suffix}" if path.suffix else f"{path.stem}.audio"

    try:
        audio = path.read_bytes()
        text = await transcribe_file(audio, filename, key=key, model=model, language=language)
    except RuntimeError as e:
        return ToolResult.fail(str(e))

    if not text:
        return ToolResult.fail("Transkript leer — kein Sprache im Audio erkannt?")

    logger.info("transcribe_audio: ok model=%s file=%s chars=%d", model, path.name, len(text))
    return ToolResult.ok(text, model=model)


TOOL = Tool(
    name="transcribe_audio",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
