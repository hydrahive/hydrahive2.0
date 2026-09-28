"""Serververwaltung: Rollen anlegen, ändern, löschen, zuweisen, entziehen
(docs/specs/discord-server-admin-tools.md, discord_member_manage).

Grenzen aus ops_guild: nie Administrator/Server verwalten, nur Rollen unterhalb
der Bot-Rolle, geschützte Personen behalten ihre Rollen.
"""
from __future__ import annotations

import re

import discord

from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, discord_errors, egress_scrub,
)
from hydrahive.communication.discord.ops_guild import (
    audit_reason, check_permissions, permission_names, permissions_from_names,
    require_actionable_member, require_guild_perm, require_role_below_bot,
    resolve_guild, resolve_member, resolve_role,
)

MAX_NAME = 100
_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _name(scope: Scope, agent_id: str, raw: object) -> str:
    name = egress_scrub(scope, agent_id, str(raw or "").strip())
    if not name or len(name) > MAX_NAME:
        raise DiscordToolError(f"Rollenname muss 1–{MAX_NAME} Zeichen lang sein.")
    return name


def _colour(raw: object) -> discord.Colour | None:
    if raw in (None, ""):
        return None
    m = _HEX.match(str(raw).strip())
    if not m:
        raise DiscordToolError("Farbe als Hex angeben, z. B. #3366ff.")
    return discord.Colour(int(m.group(1), 16))


def _perms(names: list[str] | None) -> discord.Permissions | None:
    if names is None:
        return None
    perms = permissions_from_names(names)
    check_permissions(perms)
    return perms


def _role_line(role: discord.Role) -> str:
    perms = permission_names(role.permissions)
    shown = ", ".join(perms[:8]) + (" …" if len(perms) > 8 else "")
    count = len(role.members) if hasattr(role, "members") else "?"
    return f"  {role.position:>3} · {role.name} ({role.id}) · {count} Mitgl. · {shown or 'keine Rechte'}"


async def list_roles(scope: Scope, *, guild_id: object) -> str:
    guild = await resolve_guild(scope, guild_id)
    lines = [f"Rollen auf «{guild.name}» (Position · Name · ID · Mitglieder · Rechte):"]
    lines += [_role_line(r) for r in sorted(guild.roles, key=lambda r: -r.position)]
    return "\n".join(lines)


async def create_role(scope: Scope, agent_id: str, *, guild_id: object, name: object,
                      color: object = None, permissions: list[str] | None = None,
                      mentionable: bool = False, hoist: bool = False) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_roles", "Rollen verwalten")
    role_name = _name(scope, agent_id, name)
    opts: dict = {"name": role_name, "permissions": _perms(permissions or []) or discord.Permissions.none(),
                  "mentionable": bool(mentionable), "hoist": bool(hoist)}
    if (c := _colour(color)) is not None:
        opts["colour"] = c
    with discord_errors("Rolle anlegen"):
        role = await guild.create_role(reason=audit_reason(f"Rolle «{role_name}» angelegt"), **opts)
    return f"Rolle «{role.name}» angelegt (ID {role.id}), Rechte: {permission_names(role.permissions) or 'keine'}."


async def edit_role(scope: Scope, agent_id: str, *, guild_id: object, role_id: object,
                    name: object = None, color: object = None, permissions: list[str] | None = None,
                    mentionable: bool | None = None, hoist: bool | None = None) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_roles", "Rollen verwalten")
    role = resolve_role(guild, role_id)
    require_role_below_bot(guild, role)
    changes: dict = {}
    if name is not None:
        changes["name"] = _name(scope, agent_id, name)
    if (c := _colour(color)) is not None:
        changes["colour"] = c
    if (p := _perms(permissions)) is not None:
        changes["permissions"] = p
    if mentionable is not None:
        changes["mentionable"] = bool(mentionable)
    if hoist is not None:
        changes["hoist"] = bool(hoist)
    if not changes:
        raise DiscordToolError("Nichts zu ändern — mindestens ein Feld angeben.")
    with discord_errors("Rolle ändern"):
        await role.edit(reason=audit_reason(f"Rolle «{role.name}» geändert: {', '.join(changes)}"), **changes)
    return f"Rolle «{role.name}» ({role.id}) geändert: {', '.join(changes)}."


async def delete_role(scope: Scope, *, guild_id: object, role_id: object) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_roles", "Rollen verwalten")
    role = resolve_role(guild, role_id)
    require_role_below_bot(guild, role)
    label = role.name
    with discord_errors("Rolle löschen"):
        await role.delete(reason=audit_reason(f"Rolle «{label}» gelöscht"))
    return f"Rolle «{label}» ({role.id}) gelöscht."


async def assign_role(scope: Scope, *, guild_id: object, user_id: object, role_id: object) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_roles", "Rollen verwalten")
    role = resolve_role(guild, role_id)
    require_role_below_bot(guild, role)
    member = await resolve_member(guild, user_id)
    with discord_errors("Rolle zuweisen"):
        await member.add_roles(role, reason=audit_reason(f"Rolle «{role.name}» an {member.display_name} vergeben"))
    return f"Rolle «{role.name}» an {member.display_name} ({member.id}) vergeben."


async def remove_role(scope: Scope, *, guild_id: object, user_id: object, role_id: object) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_roles", "Rollen verwalten")
    role = resolve_role(guild, role_id)
    require_role_below_bot(guild, role)
    member = await resolve_member(guild, user_id)
    require_actionable_member(scope, guild, member)
    with discord_errors("Rolle entziehen"):
        await member.remove_roles(role, reason=audit_reason(f"Rolle «{role.name}» von {member.display_name} entzogen"))
    return f"Rolle «{role.name}» von {member.display_name} ({member.id}) entzogen."
