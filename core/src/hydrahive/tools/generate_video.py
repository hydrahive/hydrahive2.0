"""Videogenerierung über OpenRouter (asynchrone Jobs-API).

OpenRouter Video läuft NICHT über chat/completions — eigene async Jobs-API:
  POST /api/v1/videos          → job_id
  GET  /api/v1/videos/{job_id} → status ("pending"|"processing"|"completed"|"failed")

Live-verifizierte Modelle (GET /api/v1/videos/models, Stand 2026-06):
  minimax/hailuo-2.3               — günstig, schnell, Image-to-Video (default)
  kwaivgi/kling-v3.0-std           — Kling v3, gutes Preis/Qualität
  bytedance/seedance-2.0-fast      — schnell
  google/veo-3.1                   — Veo 3.1 (teurer, top Qualität)

Image-to-Video: image_url als Startframe mitgeben (Pfad im Workspace → data-URI,
oder direkte https-URL). Wird intern als frame_images/first_frame gesendet —
das flache image_url-Feld ignoriert die API. Nicht alle Modelle können I2V.
Poll-Loop: max 300s, Intervall exponentiell 5s→10s→20s (Cap), dann Timeout-Fehler.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path

from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_media import save_bytes  # noqa: F401 (re-export für Tests)
from hydrahive.tools._openrouter_video import (
    download_video,
    openrouter_key,
    poll_video_job,
    submit_video_job,
)
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "minimax/hailuo-2.3"
_POLL_TIMEOUT = 300.0      # Sekunden bis Timeout-Fehler
_POLL_INTERVAL_START = 5.0
_POLL_INTERVAL_MAX = 20.0

_DESCRIPTION = (
    "Generiert ein Video aus einem Text-Prompt über OpenRouter (async Jobs-API). "
    "Optionaler Startframe via image_path (Workspace-Pfad relativ zum Workspace) für Image-to-Video. "
    "Das Video wird gespeichert und im Chat als Video-Player angezeigt. "
    "Verfügbare Modelle: minimax/hailuo-2.3 (default, Image-to-Video), "
    "kwaivgi/kling-v3.0-std, bytedance/seedance-2.0-fast, google/veo-3.1. "
    "Generierung dauert 15–90 Sekunden je nach Modell. "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "Videobeschreibung auf Englisch für beste Ergebnisse.",
        },
        "model": {
            "type": "string",
            "description": (
                "OpenRouter-Modell-ID. Default: minimax/hailuo-2.3. "
                "Weitere: kwaivgi/kling-v3.0-std, bytedance/seedance-2.0-fast, google/veo-3.1"
            ),
            "default": _DEFAULT_MODEL,
        },
        "width": {
            "type": "integer",
            "description": "Videobreite in Pixel (default 1280).",
            "default": 1280,
        },
        "height": {
            "type": "integer",
            "description": "Videohöhe in Pixel (default 720).",
            "default": 720,
        },
        "duration": {
            "type": "integer",
            "description": "Videolänge in Sekunden (default 5).",
            "default": 5,
        },
        "aspect_ratio": {
            "type": "string",
            "description": "Seitenverhältnis (default '16:9'). Weitere: '9:16', '1:1'.",
            "default": "16:9",
        },
        "image_path": {
            "type": "string",
            "description": (
                "Optionaler Startframe für Image-to-Video: Pfad relativ zum Workspace "
                "(z.B. 'generated/bild.png'). Wird als base64 an die API übergeben. "
                "Nicht alle Modelle unterstützen das — Kling und Hailuo tun es."
            ),
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

    model = (args.get("model") or get_media_model("video") or _DEFAULT_MODEL).strip()
    width = int(args.get("width") or 1280)
    height = int(args.get("height") or 720)
    duration = int(args.get("duration") or 5)
    aspect_ratio = (args.get("aspect_ratio") or "16:9").strip()
    image_path: str | None = (args.get("image_path") or "").strip() or None
    image_url: str | None = None

    if image_path:
        img_path = Path(image_path)
        if not img_path.is_absolute():
            img_path = ctx.workspace / image_path
        if not img_path.exists():
            return ToolResult.fail(f"Bild nicht gefunden: {img_path}")
        suffix = img_path.suffix.lower().lstrip(".") or "jpeg"
        mime = "image/png" if suffix == "png" else f"image/{suffix}"
        image_url = f"data:{mime};base64,{base64.b64encode(img_path.read_bytes()).decode()}"

    try:
        job_id = await submit_video_job(
            prompt, model,
            key=key, width=width, height=height,
            duration=duration, aspect_ratio=aspect_ratio,
            image_url=image_url,
        )
    except RuntimeError as e:
        return ToolResult.fail(str(e))

    # Poll-Loop mit exponentiellem Backoff
    elapsed = 0.0
    interval = _POLL_INTERVAL_START
    while elapsed < _POLL_TIMEOUT:
        await asyncio.sleep(interval)
        elapsed += interval
        interval = min(interval * 2, _POLL_INTERVAL_MAX)

        try:
            job = await poll_video_job(job_id, key=key)
        except RuntimeError as e:
            return ToolResult.fail(f"Fehler beim Job-Status-Abruf: {e}")

        status = job["status"]
        if status == "completed":
            url = job.get("url")
            if not url:
                raw = str(job.get("_raw", {}))[:400]
                return ToolResult.fail(
                    f"Job completed aber keine Download-URL in unsigned_urls. "
                    f"OpenRouter-Antwort: {raw}"
                )
            try:
                path = await download_video(url, ctx.workspace / "generated", key=key)
            except RuntimeError as e:
                return ToolResult.fail(str(e))
            logger.info("generate_video: fertig model=%s path=%s", model, path)
            return ToolResult.ok(f"Video generiert und gespeichert: {path}", model=model)

        # Doku: "in_progress" (nicht "processing")
        if status in ("failed", "cancelled", "expired"):
            error = job.get("error") or "Unbekannter Fehler"
            return ToolResult.fail(f"Video-Generierung fehlgeschlagen: {error}")

        logger.debug("generate_video: job=%s status=%s elapsed=%.0fs", job_id, status, elapsed)

    return ToolResult.fail(
        f"Timeout nach {_POLL_TIMEOUT:.0f}s — Video noch nicht fertig (job_id={job_id}). "
        "Bitte später mit demselben Prompt erneut versuchen."
    )


TOOL = Tool(
    name="generate_video",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
