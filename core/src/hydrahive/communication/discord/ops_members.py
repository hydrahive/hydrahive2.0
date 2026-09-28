"""Serververwaltung: Mitglieder — Liste, Nickname, Timeout, Kick, Ban, Unban
(docs/specs/discord-server-admin-tools.md, discord_member_manage).

Serverbesitzer, Bot und Besitzer-IDs aus der Discord-Konfiguration sind von
allen eingreifenden Aktionen ausgenommen (ops_guild.require_actionable_member).
"""
from __future__ import annotations

import datetime as dt

import discord

from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, discord_errors, egress_scrub, parse_id,
)
from hydrahive.communication.discord.ops_guild import (
    audit_reason, require_actionable_member, require_guild_perm, resolve_guild,
    resolve_member, resolve_role,
)

MAX_TIMEOUT_MINUTES = 28 * 24 * 60
MAX_NICK = 32
MAX_LIST = 100


def _reason(scope: Scope, agent_id: str, action: str, raw: object) -> str:
    text = egress_scrub(scope, agent_id, str(raw or "").strip())
    return audit_reason(f"{action} — {text}" if text else action)


def _member_line(m: discord.Member) -> str:
    roles = ", ".join(r.name for r in m.roles if not r.is_default()) or "—"
    joined = m.joined_at.date().isoformat() if m.joined_at else "?"
    bot = " · Bot" if m.bot else ""
    return f"  {m.display_name} ({m.name}, {m.id}){bot} · seit {joined} · Rollen: {roles}"


async def list_members(scope: Scope, *, guild_id: object, query: object = None,
                       role_id: object = None, limit: object = MAX_LIST) -> str:
    guild = await resolve_guild(scope, guild_id)
    needle = str(query or "").strip().casefold()
    role = resolve_role(guild, role_id) if role_id not in (None, "") else None
    rows = []
    for m in guild.members:
        if needle and needle not in m.name.casefold() and needle not in m.display_name.casefold():
            continue
        if role is not None and role not in m.roles:
            continue
        rows.append(m)
    cap = max(1, min(int(limit or MAX_LIST), MAX_LIST))
    lines = [f"Mitglieder auf «{guild.name}»: {len(rows)} Treffer"
             + (f" (erste {cap})" if len(rows) > cap else "")]
    lines += [_member_line(m) for m in sorted(rows, key=lambda m: m.display_name.casefold())[:cap]]
    return "\n".join(lines)


async def set_nickname(scope: Scope, agent_id: str, *, guild_id: object, user_id: object,
                       nickname: object) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_nicknames", "Nicknames verwalten")
    member = await resolve_member(guild, user_id)
    require_actionable_member(scope, guild, member)
    nick = egress_scrub(scope, agent_id, str(nickname or "").strip()) or None
    if nick and len(nick) > MAX_NICK:
        raise DiscordToolError(f"Nickname darf höchstens {MAX_NICK} Zeichen haben.")
    with discord_errors("Nickname setzen"):
        await member.edit(nick=nick, reason=audit_reason("Nickname " + (f"«{nick}» gesetzt" if nick else "entfernt")))
    return f"Nickname von {member.name} ({member.id}) " + (f"auf «{nick}» gesetzt." if nick else "entfernt.")


async def timeout(scope: Scope, agent_id: str, *, guild_id: object, user_id: object,
                  minutes: object, reason: object = None) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "moderate_members", "Mitglieder timeouten")
    member = await resolve_member(guild, user_id)
    require_actionable_member(scope, guild, member)
    try:
        mins = int(minutes or 0)
    except (TypeError, ValueError):
        raise DiscordToolError("minutes muss eine Zahl sein.") from None
    if mins < 0 or mins > MAX_TIMEOUT_MINUTES:
        raise DiscordToolError("Timeout höchstens 28 Tage (40320 Minuten); 0 hebt ihn auf.")
    until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=mins) if mins else None
    with discord_errors("Timeout"):
        await member.timeout(until, reason=_reason(scope, agent_id, "Timeout" if mins else "Timeout aufgehoben", reason))
    if not mins:
        return f"Timeout von {member.display_name} ({member.id}) aufgehoben."
    return f"{member.display_name} ({member.id}) für {mins} Minuten in Timeout (bis {until:%Y-%m-%d %H:%M} UTC)."


async def kick(scope: Scope, agent_id: str, *, guild_id: object, user_id: object,
               reason: object = None) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "kick_members", "Mitglieder kicken")
    member = await resolve_member(guild, user_id)
    require_actionable_member(scope, guild, member)
    with discord_errors("Kick"):
        await member.kick(reason=_reason(scope, agent_id, "Kick", reason))
    return f"{member.display_name} ({member.id}) wurde vom Server entfernt (Kick)."


async def ban(scope: Scope, agent_id: str, *, guild_id: object, user_id: object,
              reason: object = None, delete_days: object = 0) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "ban_members", "Mitglieder bannen")
    member = await resolve_member(guild, user_id)
    require_actionable_member(scope, guild, member)
    try:
        days = int(delete_days or 0)
    except (TypeError, ValueError):
        raise DiscordToolError("delete_days muss eine Zahl sein.") from None
    if not 0 <= days <= 7:
        raise DiscordToolError("delete_days muss zwischen 0 und 7 liegen.")
    with discord_errors("Bann"):
        await member.ban(reason=_reason(scope, agent_id, "Bann", reason), delete_message_days=days)
    return f"{member.display_name} ({member.id}) wurde gebannt" + (f", Nachrichten der letzten {days} Tage gelöscht." if days else ".")


async def unban(scope: Scope, agent_id: str, *, guild_id: object, user_id: object,
                reason: object = None) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "ban_members", "Mitglieder bannen")
    uid = parse_id(user_id, "Benutzer-ID")
    with discord_errors("Entbannen"):
        await guild.unban(discord.Object(id=uid), reason=_reason(scope, agent_id, "Entbannt", reason))
    return f"Benutzer {uid} wurde entbannt."
