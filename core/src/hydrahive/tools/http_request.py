from __future__ import annotations

import httpx

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Führt einen HTTP-Request aus. Gibt Status, Header und Body (max 100 KB) zurück. "
    "Methoden: GET, POST, PUT, PATCH, DELETE, HEAD."
)

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}

_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "Vollständige URL (http oder https)."},
        "method": {"type": "string", "description": "HTTP-Methode (default GET).", "default": "GET"},
        "headers": {"type": "object", "description": "Optionale Header (Key/Value)."},
        "body": {"type": "string", "description": "Request-Body (für POST/PUT/PATCH)."},
        "timeout": {"type": "integer", "description": "Timeout in Sekunden (default 30).", "default": 30},
    },
    "required": ["url"],
}

_MAX_BODY = 100_000


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    url = (args.get("url") or "").strip()
    if not url:
        return ToolResult.fail("Leere URL")
    if not (url.startswith("http://") or url.startswith("https://")):
        return ToolResult.fail("Nur http:// oder https://")

    method = (args.get("method") or "GET").upper()
    if method not in _ALLOWED_METHODS:
        return ToolResult.fail(f"Methode nicht erlaubt: {method}")

    headers = args.get("headers") or {}
    if not isinstance(headers, dict):
        return ToolResult.fail("headers muss ein Objekt sein")

    body = args.get("body")
    timeout = max(1, min(120, int(args.get("timeout", 30))))

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.request(method, url, headers=headers, content=body)
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Request fehlgeschlagen: {e}")

    text = r.text
    truncated = False
    if len(text) > _MAX_BODY:
        text = text[:_MAX_BODY]
        truncated = True

    return ToolResult.ok({
        "status": r.status_code,
        "headers": dict(r.headers),
        "body": text,
        "truncated": truncated,
    })


TOOL = Tool(name="http_request", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="web")
