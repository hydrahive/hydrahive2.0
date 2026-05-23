"""Shared helpers for Webmin XML-RPC tools."""
from __future__ import annotations

import base64
import xmlrpc.client
from typing import Any

import httpx

from hydrahive.settings import settings
from hydrahive.credentials import get_credential
from hydrahive.tools.base import ToolResult


def _base_from_pattern(pattern: str) -> str:
    return pattern.rstrip("/*").rstrip("/")


def resolve_webmin(user_id: str) -> tuple[str, Any] | tuple[None, ToolResult]:
    """Return (base_url, credential) or (None, ToolResult.fail(...))."""
    cred_name = settings.webmin_credential
    cred = get_credential(user_id, cred_name)
    if not cred:
        return None, ToolResult.fail(
            f"Kein Credential '{cred_name}' gefunden — "
            "in /credentials anlegen: type=basic, value=user:password, "
            "url_pattern=https://WEBMIN-HOST:10000/*"
        )
    base = settings.webmin_url or _base_from_pattern(cred.url_pattern)
    if not base or base == "*":
        return None, ToolResult.fail(
            "Webmin-URL unbekannt — entweder HH_WEBMIN_URL setzen oder "
            "url_pattern im Credential auf https://HOST:10000/* setzen"
        )
    return (base, cred), None


async def xmlrpc_call(
    base: str,
    cred_value: str,
    method: str,
    args: list | None = None,
    timeout: float = 30.0,
) -> tuple[bool, Any]:
    """POST an XML-RPC request to /xmlrpc.cgi.  Returns (ok, result_or_error)."""
    body = xmlrpc.client.dumps(tuple(args or []), method).encode("utf-8")
    b64 = base64.b64encode(cred_value.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64}",
        "Content-Type": "text/xml",
        "Accept": "text/xml",
    }
    try:
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            r = await client.post(f"{base}/xmlrpc.cgi", content=body, headers=headers)
    except httpx.HTTPError as exc:
        return False, f"Verbindung zu Webmin fehlgeschlagen: {exc}"

    if r.status_code == 401:
        return False, "Webmin: Authentifizierung fehlgeschlagen — Credentials prüfen"
    if r.status_code == 403:
        return False, (
            "Webmin: Zugriff verweigert — RPC-Berechtigung prüfen "
            "(Webmin → Webmin Users → Agent-User → Allowed modules → 'webmin' → rpc: Yes)"
        )

    raw = r.content
    if raw.lstrip()[:5].lower() in (b"<html", b"<!doc"):
        return False, (
            "Webmin antwortet mit HTML statt XML — wahrscheinlich hat der Agent-User "
            "keine RPC-Berechtigung oder der Webmin-User ist nicht konfiguriert"
        )

    try:
        result, _ = xmlrpc.client.loads(raw)
        return True, _to_json_safe(result[0] if result else None)
    except xmlrpc.client.Fault as exc:
        return False, f"Webmin RPC-Fehler {exc.faultCode}: {exc.faultString}"
    except Exception as exc:
        return False, f"Webmin-Antwort nicht parsebar: {exc}"


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert xmlrpc.client types to JSON-serializable equivalents."""
    if isinstance(obj, xmlrpc.client.Binary):
        try:
            return obj.data.decode("utf-8", errors="replace")
        except Exception:
            return f"<binary {len(obj.data)} bytes>"
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(x) for x in obj]
    return obj
