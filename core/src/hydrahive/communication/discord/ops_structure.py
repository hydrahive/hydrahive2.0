"""Serververwaltung: Überblick, Kategorien, Kanäle, Foren, Kanalrechte, Einladung
(docs/specs/discord-server-admin-tools.md, discord_server_manage).

Alle Aktionen nur auf freigegebenen Servern (ops_guild). Discord-Rechte des Bots
werden vorab geprüft. Namen und Themen laufen durch die Egress-Schwärzung.
"""
from __future__ import annotations

import discord

from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, discord_errors, egress_scrub, kind,
)
from hydrahive.communication.discord.ops_guild import (
    audit_reason, check_permissions, permissions_from_names, require_guild_perm,
    resolve_admin_channel, resolve_guild, resolve_role,
)

MAX_NAME = 100
MAX_TOPIC = 1024
MAX_SLOWMODE = 21600
_KINDS = ("text", "news", "forum")
_FREIGABE_HINWEIS = (
    " Für discord_read/discord_post unter Kommunikation → Discord «Kanäle für Agenten-Werkzeuge» "
    "anhaken.")


def _name(scope: Scope, agent_id: str, raw: object, what: str = "Name") -> str:
    name = egress_scrub(scope, agent_id, str(raw or "").strip())
    if not name or len(name) > MAX_NAME:
        raise DiscordToolError(f"{what} muss 1–{MAX_NAME} Zeichen lang sein.")
    return name


def _topic(scope: Scope, agent_id: str, raw: object) -> str | None:
    if raw is None:
        return None
    topic = egress_scrub(scope, agent_id, str(raw).strip())
    if len(topic) > MAX_TOPIC:
        raise DiscordToolError(f"Das Thema darf höchstens {MAX_TOPIC} Zeichen haben.")
    return topic


def _slowmode(raw: object) -> int | None:
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise DiscordToolError("slowmode muss eine Zahl in Sekunden sein.") from None
    if not 0 <= value <= MAX_SLOWMODE:
        raise DiscordToolError(f"slowmode muss zwischen 0 und {MAX_SLOWMODE} Sekunden liegen.")
    return value


def _category(guild: discord.Guild, raw: object):
    if raw in (None, ""):
        return None
    cat = guild.get_channel(int(raw)) if str(raw).isdigit() else None
    if cat is None or getattr(cat, "type", None) != discord.ChannelType.category:
        raise DiscordToolError(f"Kategorie {raw} gibt es auf diesem Server nicht (overview zeigt die IDs).")
    return cat


async def overview(scope: Scope, *, guild_id: object) -> str:
    """Struktur (Kategorien mit Kanälen), Rollen und Mitgliederzahl."""
    guild = await resolve_guild(scope, guild_id)
    lines = [f"Server «{guild.name}» ({guild.id}) · Mitglieder: {guild.member_count}", "Struktur:"]
    by_cat: dict[int | None, list] = {}
    for ch in guild.channels:
        if kind(ch) in ("text", "news", "forum"):
            cat = getattr(ch, "category", None)
            by_cat.setdefault(cat.id if cat else None, []).append(ch)
    for cat in [None, *sorted(guild.categories, key=lambda c: c.position)]:
        chans = sorted(by_cat.get(cat.id if cat else None, []), key=lambda c: getattr(c, "position", 0))
        if cat is not None:
            lines.append(f"  📁 {cat.name} ({cat.id})")
        elif not chans:
            continue
        for ch in chans:
            lines.append(f"    #{ch.name} ({ch.id}) · {kind(ch)}")
    lines.append("Rollen (Position · Name · ID):")
    for role in sorted(guild.roles, key=lambda r: -r.position):
        lines.append(f"  {role.position:>3} · {role.name} ({role.id})")
    return "\n".join(lines)


async def create_category(scope: Scope, agent_id: str, *, guild_id: object, name: object) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_channels", "Kanäle verwalten")
    cat_name = _name(scope, agent_id, name)
    with discord_errors("Kategorie anlegen"):
        cat = await guild.create_category(cat_name, reason=audit_reason(f"Kategorie «{cat_name}» angelegt"))
    return f"Kategorie «{cat.name}» angelegt (ID {cat.id})."


async def create_channel(scope: Scope, agent_id: str, *, guild_id: object, name: object,
                         kind: str = "text", category_id: object = None, topic: object = None,
                         slowmode: object = None, tags: list[str] | None = None,
                         require_tag: bool = False) -> str:
    guild = await resolve_guild(scope, guild_id)
    require_guild_perm(guild, "manage_channels", "Kanäle verwalten")
    ch_kind = str(kind or "text").lower()
    if ch_kind not in _KINDS:
        raise DiscordToolError("Kanaltyp muss text, news oder forum sein.")
    ch_name = _name(scope, agent_id, name)
    opts = {"category": _category(guild, category_id), "reason": audit_reason(f"Kanal «{ch_name}» angelegt")}
    if (t := _topic(scope, agent_id, topic)) is not None:
        opts["topic"] = t
    if (s := _slowmode(slowmode)) is not None:
        opts["slowmode_delay"] = s
    with discord_errors("Kanal anlegen"):
        if ch_kind == "forum":
            opts["available_tags"] = [discord.ForumTag(name=_name(scope, agent_id, t, "Tag-Name"))
                                      for t in (tags or [])]
            ch = await guild.create_forum(ch_name, **opts)
            if require_tag:
                await ch.edit(require_tag=True, reason=audit_reason("Tagpflicht gesetzt"))
        else:
            ch = await guild.create_text_channel(ch_name, news=(ch_kind == "news"), **opts)
    return f"Kanal #{ch.name} ({ch_kind}) angelegt (ID {ch.id}). Er ist nicht automatisch für die Werkzeuge freigegeben.{_FREIGABE_HINWEIS}"


async def edit_channel(scope: Scope, agent_id: str, *, channel_id: object, name: object = None,
                       topic: object = None, category_id: object = None, position: object = None,
                       slowmode: object = None, nsfw: bool | None = None) -> str:
    ch = await resolve_admin_channel(scope, channel_id)
    require_guild_perm(ch.guild, "manage_channels", "Kanäle verwalten")
    changes: dict = {}
    if name is not None:
        changes["name"] = _name(scope, agent_id, name)
    if (t := _topic(scope, agent_id, topic)) is not None:
        changes["topic"] = t
    if category_id is not None:
        changes["category"] = _category(ch.guild, category_id)
    if position is not None:
        changes["position"] = int(position)
    if (s := _slowmode(slowmode)) is not None:
        changes["slowmode_delay"] = s
    if nsfw is not None:
        changes["nsfw"] = bool(nsfw)
    if not changes:
        raise DiscordToolError("Nichts zu ändern — mindestens ein Feld angeben.")
    with discord_errors("Kanal ändern"):
        await ch.edit(reason=audit_reason(f"Kanal «{ch.name}» geändert: {', '.join(changes)}"), **changes)
    label = changes.get("name", getattr(ch, "name", ch.id))
    return f"Kanal «{label}» ({ch.id}) geändert: {', '.join(changes)}."


async def delete_channel(scope: Scope, *, channel_id: object) -> str:
    ch = await resolve_admin_channel(scope, channel_id)
    require_guild_perm(ch.guild, "manage_channels", "Kanäle verwalten")
    label = getattr(ch, "name", str(ch.id))
    with discord_errors("Kanal löschen"):
        await ch.delete(reason=audit_reason(f"Kanal «{label}» gelöscht"))
    return f"Kanal «{label}» ({ch.id}) gelöscht."


async def set_permissions(scope: Scope, *, channel_id: object, role_id: object,
                          allow: list[str] | None = None, deny: list[str] | None = None) -> str:
    ch = await resolve_admin_channel(scope, channel_id)
    require_guild_perm(ch.guild, "manage_roles", "Rollen verwalten")
    role = resolve_role(ch.guild, role_id)
    allowed, denied = permissions_from_names(allow), permissions_from_names(deny)
    check_permissions(allowed)
    overwrite = discord.PermissionOverwrite.from_pair(allowed, denied)
    with discord_errors("Kanalrechte setzen"):
        await ch.set_permissions(role, overwrite=overwrite,
                                 reason=audit_reason(f"Rechte von «{role.name}» in «{ch.name}» gesetzt"))
    return (f"Rechte von «{role.name}» in #{ch.name}: erlaubt {allow or []}, verboten {deny or []}.")


async def create_invite(scope: Scope, *, channel_id: object, max_age_hours: object = 24,
                        max_uses: object = 0) -> str:
    ch = await resolve_admin_channel(scope, channel_id)
    require_guild_perm(ch.guild, "create_instant_invite", "Einladung erstellen")
    hours = max(0, min(int(max_age_hours or 0), 24 * 7))
    uses = max(0, min(int(max_uses or 0), 100))
    with discord_errors("Einladung erstellen"):
        inv = await ch.create_invite(max_age=hours * 3600, max_uses=uses,
                                     reason=audit_reason(f"Einladung für «{ch.name}»"))
    ablauf = f"gültig {hours} h" if hours else "unbegrenzt gültig"
    nutzung = f"max. {uses} Nutzungen" if uses else "unbegrenzte Nutzungen"
    return f"Einladung: {inv.url} ({ablauf}, {nutzung})."
