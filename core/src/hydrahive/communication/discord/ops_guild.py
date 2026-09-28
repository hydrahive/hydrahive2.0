"""Serververwaltung: Freigabe pro Server, Rollenhierarchie, geschützte Personen,
Rechte-Grenzen (docs/specs/discord-server-admin-tools.md, Abschnitte 3 und 4).

Alle Verwaltungsoperationen (ops_structure, ops_roles, ops_members) holen sich
Server und Mitglieder ausschließlich über dieses Modul. Die Grenzen hier gelten
unabhängig von der Freigabe des Benutzers.
"""
from __future__ import annotations

import discord

from hydrahive.communication.discord import config as dc_config
from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, connected_client, fetch_any, parse_id,
)

AUDIT_PREFIX = "HydraHive-Agent"

# Rechte, die nie vergeben werden (Abschnitt 4.1).
FORBIDDEN_PERMS = {"administrator": "Administrator", "manage_guild": "Server verwalten"}

# Rechte, die nur mit Bestätigung des Benutzers vergeben werden.
RISKY_PERMS = {
    "manage_roles": "Rollen verwalten", "manage_channels": "Kanäle verwalten",
    "manage_webhooks": "Webhooks verwalten", "kick_members": "Mitglieder kicken",
    "ban_members": "Mitglieder bannen", "moderate_members": "Mitglieder timeouten",
    "manage_messages": "Nachrichten verwalten", "manage_threads": "Threads verwalten",
    "mention_everyone": "@everyone erwähnen", "manage_nicknames": "Nicknames verwalten",
    "manage_expressions": "Emojis verwalten", "manage_events": "Events verwalten",
    "view_audit_log": "Audit-Log sehen",
}

# Aliase, die discord.py als Konstruktor-Argument kennt, aber nicht beim Iterieren liefert.
_ALIASES = {"view_channel": "read_messages", "manage_emojis": "manage_expressions",
            "manage_permissions": "manage_roles"}
_VALID_PERMS = {name for name, _ in discord.Permissions.none()} | set(_ALIASES)


def audit_reason(action: str) -> str:
    return f"{AUDIT_PREFIX}: {action}"[:512]


def open_admin_scope(username: str) -> Scope:
    """Scope für Verwaltungswerkzeuge; fail-closed ohne Serverfreigabe."""
    cfg = dc_config.load(username)
    if not cfg.admin_guild_ids:
        raise DiscordToolError(
            "Es ist kein Discord-Server für die Verwaltung freigegeben — unter Kommunikation → "
            "Discord beim Server «Server verwalten» anhaken.")
    return Scope(username=username, client=connected_client(username), cfg=cfg)


def _not_admin(gid: object) -> DiscordToolError:
    return DiscordToolError(
        f"Server {gid} ist nicht für die Verwaltung freigegeben (oder der Bot ist dort nicht) — "
        "unter Kommunikation → Discord «Server verwalten» anhaken.")


async def resolve_guild(scope: Scope, raw_id: object) -> discord.Guild:
    gid = parse_id(raw_id, "Server-ID")
    guild = scope.client.get_guild(gid)
    if guild is None or str(gid) not in scope.cfg.admin_guild_ids:
        raise _not_admin(gid)
    return guild


async def resolve_admin_channel(scope: Scope, raw_id: object):
    """Kanal oder Kategorie eines freigegebenen Servers — sonst dieselbe Meldung
    wie bei unbekannten IDs, damit ein Agent über fremde Server nichts erfährt."""
    cid = parse_id(raw_id, "Kanal-ID")
    ch = await fetch_any(scope.client, cid)
    guild = getattr(ch, "guild", None)
    if ch is None or guild is None or str(guild.id) not in scope.cfg.admin_guild_ids:
        raise _not_admin(f"des Kanals {cid}")
    return ch


async def resolve_member(guild: discord.Guild, raw_id: object) -> discord.Member:
    uid = parse_id(raw_id, "Benutzer-ID")
    member = guild.get_member(uid)
    if member is None:
        try:
            member = await guild.fetch_member(uid)
        except (discord.NotFound, discord.HTTPException):
            raise DiscordToolError(f"Benutzer {uid} ist kein Mitglied dieses Servers.") from None
    return member


def resolve_role(guild: discord.Guild, raw_id: object) -> discord.Role:
    role = guild.get_role(parse_id(raw_id, "Rollen-ID"))
    if role is None:
        raise DiscordToolError("Diese Rolle gibt es auf dem Server nicht — list_roles zeigt alle.")
    return role


def require_guild_perm(guild: discord.Guild, flag: str, label: str) -> None:
    perms = guild.me.guild_permissions
    if not (perms.administrator or getattr(perms, flag, False)):
        raise DiscordToolError(f"Dem Bot fehlt auf diesem Server die Berechtigung «{label}».")


def require_role_below_bot(guild: discord.Guild, role: discord.Role) -> None:
    """Abschnitt 4.2/4.4: nur Rollen unterhalb der Bot-Rolle, nie @everyone, nie die Bot-Rolle."""
    if role.is_default():
        raise DiscordToolError("Die @everyone-Rolle wird nicht verändert.")
    if role in guild.me.roles:
        raise DiscordToolError("Die Bot-Rolle selbst wird nicht verändert.")
    if role.position >= guild.me.top_role.position:
        raise DiscordToolError(
            f"Rolle «{role.name}» liegt über oder auf Höhe der Bot-Rolle — Discord erlaubt "
            "dem Bot dort keine Änderung.")
    if getattr(role, "managed", False):
        raise DiscordToolError(f"Rolle «{role.name}» wird von einer Integration verwaltet.")


def require_actionable_member(scope: Scope, guild: discord.Guild, member: discord.Member) -> None:
    """Abschnitt 4.2/4.3: geschützte Personen und Hierarchie."""
    if member.id == guild.owner_id:
        raise DiscordToolError("Der Serverbesitzer ist geschützt.")
    if member.id == guild.me.id:
        raise DiscordToolError("Der Bot selbst ist geschützt.")
    if str(member.id) in scope.cfg.owner_user_ids:
        raise DiscordToolError(
            f"Benutzer {member.id} ist als Besitzer-ID in HydraHive eingetragen und geschützt.")
    if member.top_role.position >= guild.me.top_role.position:
        raise DiscordToolError(
            f"Die höchste Rolle von {member.display_name} liegt über oder auf Höhe der Bot-Rolle.")


def check_permissions(perms: discord.Permissions) -> None:
    """Abschnitt 4.1: Administrator und Server verwalten werden nie vergeben."""
    for flag, label in FORBIDDEN_PERMS.items():
        if getattr(perms, flag):
            raise DiscordToolError(f"Das Recht «{label}» wird von HydraHive nie vergeben.")


def risky_permission_names(perms: discord.Permissions) -> list[str]:
    return [label for flag, label in RISKY_PERMS.items() if getattr(perms, flag)]


def permissions_from_names(names: list[str] | None) -> discord.Permissions:
    """Rechte aus discord.py-Namen (z. B. send_messages); unbekannte Namen sind ein Fehler."""
    flags = {}
    for raw in names or []:
        name = str(raw).strip().lower()
        if name not in _VALID_PERMS:
            raise DiscordToolError(
                f"Unbekanntes Recht «{raw}» — gültig sind z. B. view_channel, send_messages, "
                "manage_messages, manage_threads, kick_members.")
        flags[_ALIASES.get(name, name)] = True
    return discord.Permissions(**flags)


def permission_names(perms: discord.Permissions) -> list[str]:
    return [name for name, value in perms if value]
