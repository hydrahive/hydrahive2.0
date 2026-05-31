"""Bildgenerierung über OpenRouter (synchron via chat/completions).

Live-verifizierte Modelle mit output_modalities=["image"] (Stand 2026-05-31):
  openai/gpt-5-image-mini          — günstig, schnell
  openai/gpt-5-image               — Standard
  openai/gpt-5.4-image-2           — hochqualitativ
  google/gemini-2.5-flash-image    — Gemini, schnell
  google/gemini-3-pro-image-preview — Gemini Pro
  google/gemini-3.1-flash-image-preview

Flux/DALL-E/Recraft sind auf OpenRouter NICHT über chat/completions verfügbar.
"""
from __future__ import annotations

import logging

import httpx

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "openai/gpt-5-image-mini"

_DESCRIPTION = (
    "Generiert ein Bild auf Basis eines Text-Prompts über OpenRouter. "
    "Gibt eine direkte Bild-URL zurück die im Chat angezeigt wird. "
    "Verfügbare Modelle: openai/gpt-5-image-mini (default, günstig), "
    "openai/gpt-5-image, openai/gpt-5.4-image-2, "
    "google/gemini-2.5-flash-image, google/gemini-3-pro-image-preview. "
    "Braucht einen konfigurierten OpenRouter API-Key."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "Bildbeschreibung auf Englisch für beste Ergebnisse.",
        },
        "model": {
            "type": "string",
            "description": (
                "OpenRouter-Modell-ID. Default: openai/gpt-5-image-mini. "
                "Weitere: openai/gpt-5-image, openai/gpt-5.4-image-2, "
                "google/gemini-2.5-flash-image, google/gemini-3-pro-image-preview"
            ),
            "default": _DEFAULT_MODEL,
        },
        "width": {
            "type": "integer",
            "description": "Bildbreite in Pixel (default 1024).",
            "default": 1024,
        },
        "height": {
            "type": "integer",
            "description": "Bildhöhe in Pixel (default 1024).",
            "default": 1024,
        },
    },
    "required": ["prompt"],
}


def _get_openrouter_key() -> str:
    from hydrahive.llm._config import get_provider_key, load_config
    return get_provider_key(load_config(), "openrouter")


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return ToolResult.fail("Prompt darf nicht leer sein")

    key = _get_openrouter_key()
    if not key:
        return ToolResult.fail(
            "Kein OpenRouter API-Key konfiguriert — unter Einstellungen → Anbieter hinterlegen"
        )

    model = (args.get("model") or _DEFAULT_MODEL).strip()
    width = int(args.get("width") or 1024)
    height = int(args.get("height") or 1024)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image"],
        "image": {"size": f"{width}x{height}"},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{_OPENROUTER_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        body = e.response.text[:400]
        logger.warning("generate_image HTTP-Fehler %s: %s", e.response.status_code, body)
        return ToolResult.fail(f"OpenRouter API-Fehler {e.response.status_code}: {body}")
    except httpx.HTTPError as e:
        logger.warning("generate_image Netzwerk-Fehler: %s", e)
        return ToolResult.fail(f"Netzwerk-Fehler: {e}")

    image_url = _extract_image_url(data)
    if not image_url:
        logger.warning("generate_image: keine Bild-URL in Response: %s", str(data)[:400])
        return ToolResult.fail("Keine Bild-URL in OpenRouter-Antwort gefunden")

    logger.info("generate_image: Bild generiert model=%s url=%s…", model, image_url[:60])
    return ToolResult.ok(image_url, result_type="image_url", model=model)


def _extract_image_url(data: dict) -> str | None:
    """Zieht die Bild-URL aus der OpenRouter chat/completions Antwort."""
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")

    # Strukturiertes Content-Array: [{type: "image_url", image_url: {url: "..."}}]
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image_url":
                img = block.get("image_url") or {}
                url = img.get("url") if isinstance(img, dict) else img
                if url:
                    return str(url)

    # Fallback: direkt URL-String
    if isinstance(content, str) and content.startswith("http"):
        return content

    return None


TOOL = Tool(
    name="generate_image",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
