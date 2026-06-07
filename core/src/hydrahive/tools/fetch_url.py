"""HTTP-Fetch mit transparenter Auth — Tokens kommen NIE im LLM-Kontext.

Wenn die Ziel-URL gegen das url_pattern eines Credentials matcht, wird der
Auth-Header (oder Query-Param) automatisch eingefügt. Das tool_result enthält
nur den Response-Body — keine Header (also auch keinen leakenden Authorization-
Header). Der Agent sieht den Token nie.
"""
from __future__ import annotations

import base64
import urllib.parse

from hydrahive.net.ssrf import SsrfBlocked, is_blocked_host as _is_blocked, safe_async_client
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "HTTP-Request mit automatischer Auth-Injection. "
    "Wenn unter /credentials ein passendes Profil existiert, wird der Token "
    "transparent eingehängt — kommt NIE im Output zurück. "
    "Methoden: GET, POST, PUT, PATCH, DELETE, HEAD. "
    "Für einfache Requests ohne Auth: shell_exec mit curl nutzen."
)

_MAX_BYTES = 200_000
_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}

# SSRF-Schutz (_is_blocked) lebt zentral in hydrahive.net.ssrf — siehe Import oben.


_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "Vollständige URL (https://…)"},
        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"], "default": "GET"},
        "body": {"type": "string", "description": "Request-Body (für POST/PUT/PATCH)."},
        "headers": {"type": "object", "description": "Optionale zusätzliche Header (Key/Value)."},
        "auth": {"type": "string", "description": "Optional: Credential-Profilname erzwingen."},
        "content_type": {"type": "string", "description": "Z.B. 'application/json'."},
        "timeout": {"type": "integer", "description": "Timeout in Sekunden (default 30).", "default": 30},
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


def _select_cred(user_id: str, url: str, auth_name: str | None):
    """Wählt das Auth-Credential. per-User-Credential hat Vorrang; nur wenn keins
    matcht UND kein Profil erzwungen wurde, greift die system-weite Forschungs-API-
    Registry."""
    from hydrahive.credentials import match_credential
    cred = match_credential(user_id, url, prefer_name=auth_name)
    if not cred and not auth_name:
        from hydrahive.research import match_research_api
        cred = match_research_api(url)
    return cred


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    import httpx

    url = (args.get("url") or "").strip()
    if not url:
        return ToolResult.fail("Keine URL angegeben")
    if not (url.startswith("http://") or url.startswith("https://")):
        return ToolResult.fail("Nur http:// oder https://")

    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.hostname:
            return ToolResult.fail("Ungültige URL — kein Hostname")
    except Exception:
        return ToolResult.fail("Ungültige URL")

    method = (args.get("method") or "GET").upper()
    if method not in _ALLOWED_METHODS:
        return ToolResult.fail(f"Unzulässige Methode: {method}")

    body = args.get("body") or ""
    auth_name = (args.get("auth") or "").strip() or None
    content_type = args.get("content_type") or ("application/x-www-form-urlencoded" if body else None)
    timeout = max(1, min(120, int(args.get("timeout", 30))))
    extra_headers: dict = args.get("headers") or {}

    headers: dict[str, str] = {k: str(v) for k, v in extra_headers.items()} if isinstance(extra_headers, dict) else {}
    params: dict[str, str] = {}
    auth_used: str | None = None

    # Credentials VOR SSRF-Check matchen: ein konfiguriertes Credential = Admin vertraut
    # diesem Host explizit → darf auch localhost/RFC1918 ansprechen (z.B. lokales Gitea).
    cred = _select_cred(ctx.user_id, url, auth_name)
    is_internal = _is_blocked(parsed.hostname)

    if is_internal and not cred:
        return ToolResult.fail(f"Zugriff auf interne/private Adressen gesperrt: {parsed.hostname}")

    if cred:
        auth_used = _apply_auth(cred, headers, params)

    if content_type:
        headers["Content-Type"] = content_type

    try:
        if is_internal:
            # Credential vorhanden, lokaler Host → direkter Client (kein DNS-Rebinding-Risiko).
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                r = await client.request(
                    method, url, headers=headers, params=params or None,
                    content=body.encode("utf-8") if body else None,
                )
        else:
            # safe_async_client pinnt den Connect an eine vorab validierte IP →
            # DNS-Rebinding zwischen Check und Connect ist ausgeschlossen (#206).
            async with safe_async_client(url, timeout=timeout) as client:
                r = await client.request(
                    method, url, headers=headers, params=params or None,
                    content=body.encode("utf-8") if body else None,
                )
    except SsrfBlocked as e:
        return ToolResult.fail(f"Zugriff auf interne/private Adressen gesperrt: {e}")
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
        return ToolResult.ok(out, auth_hint=auth_used)
    return ToolResult.ok(out)


TOOL = Tool(
    name="fetch_url",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="web",
)
