"""HTTP-Fetch mit transparenter Auth — Tokens kommen NIE im LLM-Kontext.

Wenn die Ziel-URL gegen das url_pattern eines Credentials matcht, wird der
Auth-Header (oder Query-Param) automatisch eingefügt. Das tool_result enthält
nur den Response-Body — keine Header (also auch keinen leakenden Authorization-
Header). Der Agent sieht den Token nie.
"""
from __future__ import annotations

import base64

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "HTTP GET oder POST gegen eine URL mit automatischer Auth-Injection. "
    "Wenn unter /credentials ein passendes Profil mit url_pattern existiert, "
    "wird der Token transparent im Authorization-/Cookie-Header eingehängt. "
    "Token kommt nicht im Output zurück. Optional `auth=<profilname>` um ein "
    "spezifisches Profil zu erzwingen."
)

_MAX_BYTES = 200_000

_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "Vollständige URL (https://…)"},
        "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
        "body": {"type": "string", "description": "Request-Body bei POST (Klartext)."},
        "auth": {"type": "string", "description": "Optional: Profilname aus /credentials erzwingen."},
        "content_type": {"type": "string", "description": "Z.B. 'application/json'. Default: 'application/x-www-form-urlencoded' bei body."},
    },
    "required": ["url"],
}


def _apply_auth(cred, headers: dict, params: dict) -> str:
    """Hängt Auth ein. Returnt Klartext-Hinweis was eingefügt wurde — wird NICHT
    in tool_result aufgenommen, nur fürs Logging."""
    if cred.type == "bearer":
        headers["Authorization"] = f"Bearer {cred.value}"
        return f"Bearer-Token via Profil {cred.name}"
    if cred.type == "basic":
        b64 = base64.b64encode(cred.value.encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {b64}"
        return f"Basic-Auth via Profil {cred.name}"
    if cred.type == "cookie":
        existing = headers.get("Cookie", "")
        headers["Cookie"] = f"{existing}; {cred.value}".strip("; ") if existing else cred.value
        return f"Cookie via Profil {cred.name}"
    if cred.type == "header" and cred.header_name:
        headers[cred.header_name] = cred.value
        return f"Header {cred.header_name} via Profil {cred.name}"
    if cred.type == "query" and cred.query_param:
        params[cred.query_param] = cred.value
        return f"Query-Param {cred.query_param} via Profil {cred.name}"
    return ""


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    import httpx
    from hydrahive.credentials import match_credential

    url = (args.get("url") or "").strip()
    if not url:
        return ToolResult.fail("Keine URL angegeben")
    method = (args.get("method") or "GET").upper()
    if method not in ("GET", "POST"):
        return ToolResult.fail(f"Unzulässige Methode: {method}")
    body = args.get("body") or ""
    auth_name = (args.get("auth") or "").strip() or None
    content_type = args.get("content_type") or ("application/x-www-form-urlencoded" if body else None)

    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    auth_used: str | None = None

    cred = match_credential(ctx.user_id, url, prefer_name=auth_name)
    if cred:
        auth_used = _apply_auth(cred, headers, params)

    if content_type:
        headers["Content-Type"] = content_type

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if method == "GET":
                r = await client.get(url, headers=headers, params=params or None)
            else:
                r = await client.post(url, headers=headers, params=params or None,
                                       content=body.encode("utf-8") if body else None)
    except httpx.HTTPError as e:
        return ToolResult.fail(f"HTTP-Fehler: {e}")

    raw = r.content
    truncated = len(raw) > _MAX_BYTES
    text = raw[:_MAX_BYTES].decode("utf-8", errors="replace")
    out: dict = {
        "url": url,
        "status_code": r.status_code,
        "method": method,
        "body": text,
        "bytes": len(raw),
        "truncated": truncated,
        "auth_used": cred.name if cred else None,
        "content_type": r.headers.get("content-type", ""),
    }
    if auth_used:
        # Hint im metadata, NICHT im body — Agent sieht's, aber der Token-Wert nicht
        return ToolResult.ok(out, auth_hint=auth_used)
    return ToolResult.ok(out)


TOOL = Tool(
    name="fetch_url",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="web",
)
