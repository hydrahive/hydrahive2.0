from __future__ import annotations

import ipaddress
import urllib.parse

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

# SSRF-Protection: Block private/internal IP ranges
_BLOCKED_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # localhost
    ipaddress.ip_network("10.0.0.0/8"),       # private
    ipaddress.ip_network("172.16.0.0/12"),    # private
    ipaddress.ip_network("192.168.0.0/16"),   # private
    ipaddress.ip_network("169.254.0.0/16"),   # link-local (AWS/GCP metadata)
    ipaddress.ip_network("::1/128"),          # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),         # IPv6 private (ULA)
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


def _is_blocked_ip(hostname: str) -> bool:
    """Check if hostname resolves to a blocked IP range."""
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in net for net in _BLOCKED_RANGES)
    except ValueError:
        # Not a valid IP address, will be resolved by httpx
        return False


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    url = (args.get("url") or "").strip()
    if not url:
        return ToolResult.fail("Leere URL")
    if not (url.startswith("http://") or url.startswith("https://")):
        return ToolResult.fail("Nur http:// oder https://")

    # SSRF-Protection: Check if URL points to blocked IP range
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if hostname and _is_blocked_ip(hostname):
            return ToolResult.fail(f"Zugriff auf interne IPs gesperrt: {hostname}")
    except Exception:
        return ToolResult.fail("Ungültige URL")

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
