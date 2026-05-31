"""Vision-Input-Tool — schickt ein Bild an ein vision-fähiges Modell (#153).

Deckt den Fall: Agent analysiert ein Bild, das entweder
  - als lokaler Dateipfad (absolut, im Workspace) vorliegt — z.B. von generate_image
  - oder als http(s)-URL

Das Bild wird als `image_url`-Block in einer chat/completions-Anfrage verpackt.
Base64 für lokale Dateien (≤5 MB), direkte URL für http(s).

Modell-Wahl: Pflicht-Parameter `model` optional. Default = google/gemini-2.5-flash
(günstig, schnell, 169 Vision-Modelle auf OpenRouter). Der Caller kann z.B. auf
gpt-4o oder claude-3-5-sonnet wechseln wenn er will.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

import httpx

from hydrahive.tools._openrouter_media import openrouter_key
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "google/gemini-2.5-flash"
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
_TIMEOUT = 60.0

_DESCRIPTION = (
    "Analysiert ein Bild (lokaler Pfad oder URL) mit einem Vision-fähigen KI-Modell. "
    "Gibt eine Textantwort auf die gestellte Frage zurück. "
    "Nutze das, um Bilder zu beschreiben, Text darin zu lesen, Objekte zu erkennen o.Ä. "
    "Das Modell muss Vision unterstützen (z.B. Gemini, GPT-4o, Claude 3+). "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "image": {
            "type": "string",
            "description": (
                "Absoluter Dateipfad (z.B. /var/lib/hydrahive2/workspaces/…/bild.png) "
                "oder http(s)-URL des Bildes."
            ),
        },
        "question": {
            "type": "string",
            "description": "Was soll das Modell zum Bild beantworten oder analysieren?",
        },
        "model": {
            "type": "string",
            "description": (
                "Vision-fähiges OpenRouter-Modell. "
                "Default: google/gemini-2.5-flash. "
                "Weitere: openai/gpt-4o, anthropic/claude-3-5-sonnet, google/gemini-2.5-pro"
            ),
            "default": _DEFAULT_MODEL,
        },
    },
    "required": ["image", "question"],
}


def _image_to_content_block(image: str) -> dict | str:
    """Bild-Pfad oder URL → OpenAI-Format image_url-Block.

    Gibt einen dict-Block zurück oder einen str (Fehler-Meldung wenn Datei fehlt/zu groß).
    """
    if image.startswith(("http://", "https://")):
        return {"type": "image_url", "image_url": {"url": image}}

    path = Path(image)
    if not path.exists():
        return f"Bilddatei nicht gefunden: {image}"
    if not path.is_file():
        return f"Pfad ist kein File: {image}"

    size = path.stat().st_size
    if size > _MAX_IMAGE_BYTES:
        mb = size / (1024 * 1024)
        return f"Bild zu groß ({mb:.1f} MB) — maximal {_MAX_IMAGE_BYTES // (1024*1024)} MB"

    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    b64 = base64.standard_b64encode(raw).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    image = (args.get("image") or "").strip()
    question = (args.get("question") or "").strip()
    if not image:
        return ToolResult.fail("'image' darf nicht leer sein")
    if not question:
        return ToolResult.fail("'question' darf nicht leer sein")

    key = openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    model = (args.get("model") or _DEFAULT_MODEL).strip()

    image_block = _image_to_content_block(image)
    if isinstance(image_block, str):
        return ToolResult.fail(image_block)

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                image_block,
                {"type": "text", "text": question},
            ],
        }],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _OPENROUTER_CHAT_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                body = resp.text[:400]
                logger.warning("analyze_image HTTP %s: %s", resp.status_code, body)
                if resp.status_code == 400 and "vision" in body.lower():
                    return ToolResult.fail(
                        f"Modell '{model}' unterstützt keine Bilder — "
                        "Vision-fähiges Modell wählen (z.B. google/gemini-2.5-flash, openai/gpt-4o)"
                    )
                return ToolResult.fail(f"OpenRouter API-Fehler {resp.status_code}: {body}")
            data = resp.json()
    except httpx.HTTPError as e:
        logger.warning("analyze_image Netzwerk-Fehler: %s", e)
        return ToolResult.fail(f"Netzwerk-Fehler: {e}")

    text = _extract_text(data)
    if not text:
        logger.warning("analyze_image: keine Textantwort in Response: %s", str(data)[:400])
        return ToolResult.fail("Keine Textantwort in OpenRouter-Antwort")

    logger.info("analyze_image: ok model=%s image=%s…", model, image[:60])
    return ToolResult.ok(text)


def _extract_text(data: dict) -> str | None:
    """Text aus chat/completions-Antwort extrahieren."""
    choices = data.get("choices") or []
    if not choices:
        return None
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        text = "".join(parts).strip()
        return text or None
    return None


TOOL = Tool(
    name="analyze_image",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
