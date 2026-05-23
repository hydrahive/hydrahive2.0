"""Webmin RPC-Bridge — beliebige Webmin-Module aufrufen.

Der Agent hat einen eigenen Webmin-Account. Was er darf, konfiguriert
der Admin in den Webmin-ACLs (Webmin → Webmin Users → Agent-Account).
Credentials kommen aus dem Credential-Store — niemals im Output sichtbar.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Ruft beliebige Webmin-Module auf (RPC-Bridge). "
    "Der Agent hat einen eigenen Webmin-Account — was er darf, "
    "konfiguriert der Admin unter Webmin → Webmin Users. "
    "Beispiele: module='net', path='index.cgi', params={'action': 'list'} "
    "oder module='proc', params={'action': 'list'}. "
    "Credentials kommen aus dem Webmin-Profil — niemals im Output sichtbar."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "module": {
            "type": "string",
            "description": "Webmin-Modul (z.B. 'net', 'proc', 'filemin', 'syslog', 'software').",
        },
        "path": {
            "type": "string",
            "description": "Pfad innerhalb des Moduls (default: 'index.cgi').",
            "default": "index.cgi",
        },
        "method": {
            "type": "string",
            "enum": ["GET", "POST"],
            "default": "GET",
            "description": "HTTP-Methode.",
        },
        "params": {
            "type": "object",
            "description": "Query- oder POST-Form-Parameter als Key/Value-Objekt.",
        },
    },
    "required": ["module"],
}

_MAX_RESPONSE_BYTES = 100_000


def _base_from_pattern(pattern: str) -> str:
    return pattern.rstrip("/*").rstrip("/")


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    import base64
    import httpx
    from hydrahive.credentials import get_credential
    from hydrahive.settings import settings

    cred_name = settings.webmin_credential
    cred = get_credential(ctx.user_id, cred_name)
    if not cred:
        return ToolResult.fail(
            f"Kein Credential '{cred_name}' gefunden — "
            "in /credentials anlegen: type=basic, value=user:password, "
            "url_pattern=https://WEBMIN-HOST:10000/*"
        )

    base = settings.webmin_url or _base_from_pattern(cred.url_pattern)
    if not base or base == "*":
        return ToolResult.fail(
            "Webmin-URL unbekannt — entweder HH_WEBMIN_URL setzen oder "
            "url_pattern im Credential auf https://HOST:10000/* setzen"
        )

    module = (args.get("module") or "").strip()
    if not module:
        return ToolResult.fail("module ist erforderlich")

    path = (args.get("path") or "index.cgi").strip().lstrip("/")
    method = (args.get("method") or "GET").upper()
    params: dict = args.get("params") or {}

    b64 = base64.b64encode(cred.value.encode()).decode()
    headers = {"Authorization": f"Basic {b64}"}
    url = f"{base}/{module}/{path}"

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            if method == "POST":
                r = await client.post(url, data=params, headers=headers)
            else:
                r = await client.get(url, params=params or None, headers=headers)
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Webmin-Request fehlgeschlagen: {e}")

    if r.status_code == 401:
        return ToolResult.fail("Webmin: Authentifizierung fehlgeschlagen — Credentials prüfen")
    if r.status_code == 403:
        return ToolResult.fail(
            f"Webmin: Zugriff auf '{module}/{path}' verweigert — "
            "Admin muss ACL-Berechtigung für dieses Modul erteilen"
        )

    raw = r.content
    truncated = len(raw) > _MAX_RESPONSE_BYTES

    try:
        body = r.json()
    except Exception:
        body = raw[:_MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")

    return ToolResult.ok(
        {
            "url": url,
            "status_code": r.status_code,
            "truncated": truncated,
            "response": body,
        },
        auth_hint=f"Basic via Profil {cred.name}",
    )


TOOL = Tool(
    name="webmin_call",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="system",
)
