"""Webmin System-Status — CPU, RAM, Disk, Load, Uptime, optional SMART-Temps.

Nutzt Webmin XML-RPC (/xmlrpc.cgi) statt CGI-Direkt-Calls.
Voraussetzung: Agent-User braucht RPC-Berechtigung in den Webmin ACLs.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest System-Monitoring-Daten vom Webmin-Server via XML-RPC: CPU-Last, RAM-Auslastung, "
    "Disk-Belegung, Load-Average, Uptime, Prozess-Anzahl. "
    "Mit include_smart=true werden zusätzlich Disk-Temperaturen (SMART) abgefragt. "
    "Credentials kommen aus dem Webmin-Profil im Credential-Store — niemals im Output sichtbar. "
    "Voraussetzung: Agent-User braucht RPC-Berechtigung "
    "(Webmin → Webmin Users → User → Allowed modules → 'webmin' → rpc: Yes)."
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
    from hydrahive.tools._webmin import resolve_webmin, xmlrpc_call

    resolved, err = resolve_webmin(ctx.user_id)
    if err:
        return err
    base, cred = resolved

    ok, data = await xmlrpc_call(base, cred.value, "system-status::get_collected_info")
    if not ok:
        return ToolResult.fail(data)

    result: dict = {"source": base, "system": data}

    if args.get("include_smart", False):
        ok_s, smart = await xmlrpc_call(base, cred.value, "system-status::get_current_drive_temps")
        result["smart"] = smart if ok_s else {"error": smart}

    return ToolResult.ok(result, auth_hint=f"Basic via Profil {cred.name}")


TOOL = Tool(
    name="webmin_status",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="system",
)
