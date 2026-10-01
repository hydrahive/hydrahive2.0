"""Argumentabhängige Bestätigung für die Discord-Verwaltungswerkzeuge.

Der Runner ruft `confirm_reason(tool_name, args)` pro Aufruf auf (wie
`shell_confirm_reason` für shell_exec). Liefert die Begründung fürs
Bestätigungs-Popup oder None, wenn die Aktion ohne Nachfrage laufen darf
(docs/specs/discord-server-admin-tools.md, Abschnitt 5).
"""
from __future__ import annotations

_SERVER_CONFIRM = {
    "delete_channel": "Einen Kanal löschen lässt sich nicht rückgängig machen.",
    "set_permissions": "Rechte einer Rolle in einem Kanal werden geändert.",
}

_MEMBER_CONFIRM = {
    "delete_role": "Eine Rolle löschen lässt sich nicht rückgängig machen.",
    "kick": "Kick: Das Mitglied wird vom Server entfernt.",
    "ban": "Bann: Das Mitglied wird dauerhaft ausgeschlossen.",
    "assign_role": "Eine Rolle wird vergeben — sie kann Rechte enthalten.",
}

_ROLE_RIGHTS_ACTIONS = {"create_role", "edit_role"}

TOOL_SERVER = "discord_server_manage"
TOOL_MEMBER = "discord_member_manage"


def _names(value) -> list[str]:
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(v) for v in (value or [])]


def _risky(names: list[str]) -> list[str]:
    from hydrahive.communication.discord.ops_access import DiscordToolError
    from hydrahive.communication.discord.ops_guild import (
        FORBIDDEN_PERMS, RISKY_PERMS, permissions_from_names,
    )
    labels = {**RISKY_PERMS, **FORBIDDEN_PERMS}
    found = []
    for name in names:
        try:
            permissions = permissions_from_names([name])
        except DiscordToolError:
            continue
        found.extend(label for flag, label in labels.items() if getattr(permissions, flag))
    return list(dict.fromkeys(found))


def confirm_reason(tool_name: str, args: dict) -> str | None:
    action = str((args or {}).get("action") or "").strip().lower()
    if tool_name == TOOL_SERVER:
        return _SERVER_CONFIRM.get(action)
    if tool_name != TOOL_MEMBER:
        return None
    if action in _MEMBER_CONFIRM:
        return _MEMBER_CONFIRM[action]
    if action in _ROLE_RIGHTS_ACTIONS:
        risky = _risky(_names((args or {}).get("permissions")))
        if risky:
            return f"Die Rolle erhält riskante Rechte: {', '.join(risky)}."
    return None
