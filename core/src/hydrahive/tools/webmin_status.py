"""Webmin System-Status — CPU, RAM, Disk, Load, Uptime, optional SMART-Temps."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest System-Monitoring-Daten vom Webmin-Server: CPU-Last, RAM-Auslastung, "
    "Disk-Belegung, Load-Average, Uptime, Prozess-Anzahl. "
    "Mit include_smart=true werden zusätzlich Disk-Temperaturen (SMART) abgefragt. "
    "Credentials kommen aus dem Webmin-Profil im Credential-Store — niemals im Output sichtbar."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "include_smart": {
            "type": "boolean",
            "description": "Disk-SMART-Temperaturen abfragen (default false).",
            "default": False,
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    import base64
    import httpx
    from hydrahive.credentials import get_credential
    from hydrahive.settings import settings

    if not settings.webmin_url:
        return ToolResult.fail("Webmin nicht konfiguriert (HH_WEBMIN_URL fehlt)")

    cred_name = settings.webmin_credential
    cred = get_credential(ctx.user_id, cred_name)
    if not cred:
        return ToolResult.fail(
            f"Kein Credential '{cred_name}' gefunden — "
            "bitte in /credentials anlegen (type: basic, value: user:password)"
        )

    b64 = base64.b64encode(cred.value.encode()).decode()
    headers = {"Authorization": f"Basic {b64}"}
    base = settings.webmin_url

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            r = await client.get(
                f"{base}/system-status/index.cgi",
                params={"action": "get"},
                headers=headers,
            )
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Verbindung zu Webmin fehlgeschlagen: {e}")

    if r.status_code == 401:
        return ToolResult.fail("Webmin: Authentifizierung fehlgeschlagen — Credentials prüfen")
    if r.status_code != 200:
        return ToolResult.fail(f"Webmin antwortet mit HTTP {r.status_code}")

    try:
        payload = r.json()
        data = payload.get("data", payload)
    except Exception:
        return ToolResult.fail(f"Webmin-Antwort kein JSON: {r.text[:500]}")

    result: dict = {"source": base, "system": data}

    if args.get("include_smart", False):
        try:
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                sr = await client.get(
                    f"{base}/smart-status/index.cgi",
                    params={"action": "get"},
                    headers=headers,
                )
            if sr.status_code == 200:
                result["smart"] = sr.json()
            else:
                result["smart"] = {"error": f"HTTP {sr.status_code}"}
        except Exception as e:
            result["smart"] = {"error": str(e)}

    return ToolResult.ok(result, auth_hint=f"Basic via Profil {cred.name}")


TOOL = Tool(
    name="webmin_status",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="system",
)
