"""Bildgenerierung über OpenRouter (synchron via chat/completions).

Live-verifizierte Modelle mit output_modalities=["image"] (Stand 2026-05-31):
  openai/gpt-5-image-mini          — günstig, schnell (default)
  openai/gpt-5-image               — Standard
  openai/gpt-5.4-image-2           — hochqualitativ
  google/gemini-2.5-flash-image    — Gemini, schnell
  google/gemini-3-pro-image-preview — Gemini Pro

OpenRouter liefert das Bild als data:-URI (base64, ~3 MB) in
`message.images[].image_url.url`. Die data-URI darf NICHT ins LLM-Kontext —
sie wird im Agent-Workspace gespeichert (dort wo /api/files ausliefert), nur
der Pfad geht zurück. Echte HTTP-URLs (falls ein Modell sie liefert) werden
direkt als image_url-Result durchgereicht.
"""
from __future__ import annotations

import base64
import binascii
import logging
from pathlib import Path

import httpx

from hydrahive.tools._openrouter_media import openrouter_key, save_bytes
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "openai/gpt-5-image-mini"
_TIMEOUT = 180.0  # Bildgenerierung dauert (gpt-5-image ~60-90s)

_DESCRIPTION = (
    "Generiert ein Bild auf Basis eines Text-Prompts über OpenRouter. "
    "Das Bild wird gespeichert und im Chat angezeigt. "
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
    return openrouter_key()


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
        "modalities": ["image", "text"],
        "image": {"size": f"{width}x{height}"},
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
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

    url = _extract_image_url(data)
    if not url:
        logger.warning("generate_image: keine Bild-URL in Response: %s", str(data)[:400])
        return ToolResult.fail("Keine Bild-URL in OpenRouter-Antwort gefunden")

    # data:-URI → im Workspace speichern (base64 NIE ins LLM); echte URL → direkt nutzen.
    # Workspace liegt unter data_dir/workspaces → von /api/files ausgeliefert.
    path, err = _persist_data_uri(url, ctx.workspace / "generated")
    if err:
        return ToolResult.fail(err)
    if path is not None:
        logger.info("generate_image: Bild gespeichert model=%s path=%s", model, path)
        return ToolResult.ok(f"Bild generiert und gespeichert: {path}", model=model)

    logger.info("generate_image: Bild-URL model=%s url=%s…", model, url[:60])
    return ToolResult.ok(url, result_type="image_url", model=model)


def _extract_image_url(data: dict) -> str | None:
    """Zieht die Bild-URL/data-URI aus der OpenRouter chat/completions Antwort.

    Echtes Format (gpt-5-image, gemini-*-image): message.images[].image_url.url
    Fallback: content-Array mit image_url-Blöcken; oder content als http-String.
    """
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}

    for img in message.get("images") or []:
        if isinstance(img, dict):
            inner = img.get("image_url")
            url = inner.get("url") if isinstance(inner, dict) else inner
            if url:
                return str(url)

    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image_url":
                inner = block.get("image_url")
                url = inner.get("url") if isinstance(inner, dict) else inner
                if url:
                    return str(url)

    if isinstance(content, str) and content.startswith("http"):
        return content

    return None


def _persist_data_uri(url: str, dest_dir: Path) -> tuple[Path | None, str | None]:
    """data:-URI → Datei. Gibt (path, None) bei Erfolg, (None, error) bei Fehler.

    Für echte HTTP-URLs (kein data:-Präfix): (None, None) — kein Speichern nötig,
    der Aufrufer reicht die URL direkt durch.
    """
    if not url.startswith("data:"):
        return None, None
    try:
        header, b64 = url.split(",", 1)
        mime = header.split(";")[0].removeprefix("data:")  # "image/png"
        ext = (mime.split("/")[-1] or "png").lower()
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error) as e:
        return None, f"Bild-Daten ungültig (data-URI nicht dekodierbar): {e}"

    return save_bytes(raw, dest_dir, ext), None


TOOL = Tool(
    name="generate_image",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="media",
)
