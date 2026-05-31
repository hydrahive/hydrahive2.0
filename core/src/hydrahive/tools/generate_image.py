"""Bildgenerierung über OpenRouter (synchron via chat/completions).

Unterstützte Modelle (Auswahl):
  openrouter/black-forest-labs/flux-1.1-pro   — hochqualitativ, $0.04/Bild
  openrouter/openai/dall-e-3                  — DALL-E 3, $0.04–0.08/Bild
  openrouter/recraft-ai/recraft-v3            — Vektor-Style, $0.04/Bild
"""
from __future__ import annotations

import logging

import httpx

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "openrouter/black-forest-labs/flux-1.1-pro"

_DESCRIPTION = (
    "Generiert ein Bild auf Basis eines Text-Prompts über OpenRouter. "
    "Gibt eine direkte Bild-URL zurück die im Chat angezeigt wird. "
    "Modell per Parameter wählbar (default: Flux 1.1 Pro). "
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
                "OpenRouter-Modell-ID. Default: openrouter/black-forest-labs/flux-1.1-pro. "
                "Weitere: openrouter/openai/dall-e-3, openrouter/recraft-ai/recraft-v3"
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


def _strip_provider_prefix(model: str) -> str:
    """'openrouter/black-forest-labs/flux-1.1-pro' → 'black-forest-labs/flux-1.1-pro'."""
    if model.startswith("openrouter/"):
        return model[len("openrouter/"):]
    return model


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
    api_model = _strip_provider_prefix(model)

    payload = {
        "model": api_model,
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
        body = e.response.text[:400] if hasattr(e, "response") else ""
        logger.warning("generate_image HTTP-Fehler %s: %s", e.response.status_code, body)
        return ToolResult.fail(f"OpenRouter API-Fehler {e.response.status_code}: {body}")
    except httpx.HTTPError as e:
        logger.warning("generate_image Netzwerk-Fehler: %s", e)
        return ToolResult.fail(f"Netzwerk-Fehler: {e}")

    # Bild-URL aus Response extrahieren
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

    # Fallback: Content ist direkt ein URL-String
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
