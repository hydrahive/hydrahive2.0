"""Webmin RPC-Bridge — beliebige Webmin-Modul-Funktionen via XML-RPC aufrufen.

Aufruf: module + function + optionale args-Liste → Webmin führt module::function(args) aus.
Beispiele:
  module="cron",   function="list_cron_jobs"
  module="net",    function="active_interfaces"
  module="proc",   function="list_processes"
  module="software", function="list_packages"
  module="system-status", function="get_collected_info"

Voraussetzung: Agent-User braucht RPC-Berechtigung in den Webmin ACLs.
"""
from __future__ import annotations

import json

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Ruft beliebige Webmin-Modul-Funktionen via XML-RPC auf (module::function). "
    "Beispiele: module='cron' function='list_cron_jobs'; "
    "module='net' function='active_interfaces'; "
    "module='proc' function='list_processes'; "
    "module='software' function='list_packages'. "
    "Voraussetzung: Agent-User braucht RPC-Berechtigung "
    "(Webmin → Webmin Users → User → Allowed modules → 'webmin' → rpc: Yes). "
    "Credentials kommen aus dem Webmin-Profil — niemals im Output sichtbar."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "module": {
            "type": "string",
            "description": (
                "Webmin-Modul-Name, entspricht dem Verzeichnisnamen "
                "(z.B. 'cron', 'net', 'proc', 'software', 'system-status')."
            ),
        },
        "function": {
            "type": "string",
            "description": (
                "Perl-Funktionsname im Modul-Lib "
                "(z.B. 'list_cron_jobs', 'active_interfaces', 'list_processes')."
            ),
        },
        "args": {
            "type": "array",
            "description": "Argumente für die Funktion als JSON-Array (optional).",
            "items": {},
        },
    },
    "required": ["module", "function"],
}

_MAX_RESPONSE_CHARS = 50_000


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.tools._webmin import resolve_webmin, xmlrpc_call

    resolved, err = resolve_webmin(ctx.user_id)
    if err:
        return err
    base, cred = resolved

    module = (args.get("module") or "").strip()
    function = (args.get("function") or "").strip()
    call_args: list = args.get("args") or []

    if not module:
        return ToolResult.fail("module ist erforderlich")
    if not function:
        return ToolResult.fail("function ist erforderlich")

    method = f"{module}::{function}"
    ok, data = await xmlrpc_call(base, cred.value, method, call_args)
    if not ok:
        return ToolResult.fail(data)

    try:
        serialized = json.dumps(data, default=str)
        truncated = len(serialized) > _MAX_RESPONSE_CHARS
        response = serialized[:_MAX_RESPONSE_CHARS] if truncated else json.loads(serialized)
    except Exception:
        response = str(data)[:_MAX_RESPONSE_CHARS]
        truncated = False

    return ToolResult.ok(
        {"method": method, "truncated": truncated, "response": response},
        auth_hint=f"Basic via Profil {cred.name}",
    )


TOOL = Tool(
    name="webmin_call",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="system",
)
