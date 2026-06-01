"""OpenRouter Audio-Transkription (OpenAI-kompatible Whisper-API).

POST /api/v1/audio/transcriptions — multipart/form-data mit `file` + `model`.
Response: {"text": "..."}

Andere als die synchronen Chat-Calls oder die async Video-Jobs ist das ein
einmaliger multipart-Upload — kein Polling nötig.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_TRANSCRIBE_URL = "https://openrouter.ai/api/v1/audio/transcriptions"


def openrouter_key() -> str:
    from hydrahive.llm._config import openrouter_key as _key
    return _key()


async def transcribe_file(
    audio: bytes,
    filename: str,
    *,
    key: str,
    model: str,
    language: str | None = None,
) -> str:
    """Schickt Audio-Bytes an OpenRouter Whisper-API. Gibt Transkript zurück.

    Raises RuntimeError bei API- oder Netzwerk-Fehler.
    """
    files: dict = {"file": (filename, audio)}
    data: dict = {"model": model}
    if language:
        data["language"] = language

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                _TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {key}"},
                files=files,
                data=data,
            )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"OpenRouter Transcribe Fehler {resp.status_code}: {resp.text[:400]}"
                )
            result = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Netzwerk-Fehler beim Transkribieren: {e}") from e

    text = result.get("text") or ""
    logger.info("transcribe_file: ok model=%s chars=%d", model, len(text))
    return text.strip()
