"""Lesende Discord-Operationen der Agenten-Tools + Kanal-Katalog fürs UI."""
from __future__ import annotations

import discord

from hydrahive.communication.discord import ops_format as fmt
from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, discord_errors, kind, fetch_any, parse_id, permissions,
    resolve_channel,
)

MAX_LIMIT = 50
DEFAULT_LIMIT = 20
_KIND_LABEL = {"text": "Textkanal", "news": "Ankündigungskanal", "forum": "Forum",
               "thread": "Forum-Beitrag/Thread"}


def _limit(raw: object) -> int:
    try:
        return max(1, min(int(raw or DEFAULT_LIMIT), MAX_LIMIT))
    except (TypeError, ValueError):
        return DEFAULT_LIMIT


def catalog(client: discord.Client) -> list[dict]:
    """Alle Text-/Ankündigungs-/Forum-Kanäle, die der Bot sehen darf (für die UI-Auswahl)."""
    rows: list[tuple[tuple, dict]] = []
    for guild in client.guilds:
        for ch in guild.channels:
            k = kind(ch)
            if k not in ("text", "news", "forum"):
                continue
            perms = ch.permissions_for(guild.me)
            if not perms.view_channel:
                continue
            order = (guild.name.casefold(), ch.category.position if ch.category else -1, ch.position)
            rows.append((order, {
                "id": str(ch.id), "name": ch.name, "kind": k,
                "guild_id": str(guild.id), "guild": guild.name,
                "category": ch.category.name if ch.category else "",
                "can_send": bool(perms.send_messages),
            }))
    rows.sort(key=lambda r: r[0])
    return [row for _, row in rows]


async def list_channels(scope: Scope) -> str:
    lines = [f"Freigegebene Discord-Kanäle ({len(scope.cfg.tool_channel_ids)}). "
             "Forum-Beiträge darin sind automatisch mit freigegeben."]
    for raw in scope.cfg.tool_channel_ids:
        ch = await fetch_any(scope.client, int(raw)) if raw.isdigit() else None
        k = kind(ch) if ch is not None else None
        if ch is None or k is None:
            lines.append(f"- {raw}: nicht erreichbar (gelöscht, Bot nicht im Server oder "
                         "kein Zugriff)")
            continue
        perms = permissions(ch)
        can_write = perms.send_messages_in_threads if k == "thread" else perms.send_messages
        line = (f"- {ch.id} · #{fmt.neutralize(ch.name)} · {_KIND_LABEL[k]} · Server "
                f"«{fmt.neutralize(ch.guild.name)}» · "
                f"{'lesen+schreiben' if can_write else 'nur lesen'}")
        if k == "forum":
            tags = ", ".join(fmt.tag_label(t) for t in ch.available_tags) or "(keine)"
            line += f"\n    Tags: {tags}"
            if ch.flags.require_tag:
                line += "\n    Neue Beiträge brauchen mindestens einen Tag."
        lines.append(line)
    return "\n".join(lines)


async def read(scope: Scope, channel_id: object, *, limit: object = None,
               before: object = None) -> str:
    ch = await resolve_channel(scope, channel_id)
    k = kind(ch)
    n = _limit(limit)
    with discord_errors("Lesen"):
        if k == "forum":
            return await _read_forum(ch, n)
        return await _read_messages(ch, k, n, before)


def _thread_line(t: discord.Thread) -> str:
    tags = ", ".join(tag.name for tag in t.applied_tags)
    state = [s for s, on in (("archiviert", t.archived), ("gesperrt", t.locked)) if on]
    last = discord.utils.snowflake_time(t.last_message_id) if t.last_message_id else t.created_at
    return (f"[Beitrag {t.id}] «{fmt.neutralize(t.name)}»"
            + (f" · Tags: {fmt.neutralize(tags)}" if tags else "")
            + f" · von User-ID {t.owner_id} · {t.message_count} Antworten"
            + f" · erstellt {fmt.ts(t.created_at)} · letzte Aktivität {fmt.ts(last)}"
            + (f" · {', '.join(state)}" if state else ""))


async def _read_forum(forum: discord.ForumChannel, n: int) -> str:
    active = [t for t in await forum.guild.active_threads() if t.parent_id == forum.id]
    active.sort(key=lambda t: t.last_message_id or t.id, reverse=True)
    threads = active[:n]
    if len(threads) < n and permissions(forum).read_message_history:
        async for t in forum.archived_threads(limit=n - len(threads)):
            threads.append(t)
    head = (f"Forum #{fmt.neutralize(forum.name)} ({forum.id}) — {len(threads)} Beiträge, "
            "aktive zuerst. Inhalt eines Beitrags: discord_read mit dessen ID.")
    if not threads:
        return head + "\n(Keine Beiträge.)"
    return head + "\n" + fmt.wrap_untrusted("\n".join(_thread_line(t) for t in threads))


async def _read_messages(ch: discord.abc.Messageable, k: str, n: int, before: object) -> str:
    anchor = discord.Object(id=parse_id(before, "before-ID")) if before else None
    msgs = [m async for m in ch.history(limit=n, before=anchor)]
    more = len(msgs) == n
    msgs.reverse()
    head = f"{_KIND_LABEL[k]} #{fmt.neutralize(ch.name)} ({ch.id})"
    if k == "thread" and ch.parent_id:
        # Forum-Beitrag: die Eröffnung ist die erste Nachricht im Thread selbst
        # (ID == Thread-ID) und kommt daher schon über history() mit.
        tags = ", ".join(t.name for t in ch.applied_tags)
        head += f" in Kanal {ch.parent_id}" + (f" · Tags: {fmt.neutralize(tags)}" if tags else "")
        state = [s for s, on in (("archiviert", ch.archived), ("gesperrt", ch.locked)) if on]
        if state:
            head += f" · {', '.join(state)}"
    head += f" — {len(msgs)} Nachrichten, älteste zuerst."
    if more and msgs:
        head += f" Ältere: discord_read mit before={msgs[0].id}."
    if not msgs:
        return head + "\n(Keine Nachrichten.)"
    body = "\n\n".join(fmt.format_message(m) for m in msgs)
    return head + "\n" + fmt.wrap_untrusted(body)


__all__ = ["DiscordToolError", "catalog", "list_channels", "read"]
