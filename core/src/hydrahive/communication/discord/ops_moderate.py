"""Moderierende Discord-Operationen: Beitrag verwalten, anpinnen, löschen.

Nur in Kanälen aus `moderation_channel_ids` (docs/specs/discord-moderation-tools.md).
Aktionen tragen einen Audit-Log-Grund, wo discord.py das zulässt. Gelöschter Inhalt
wird nie zurückgegeben — er könnte genau das Secret sein, das entfernt werden soll.
"""
from __future__ import annotations

import discord

from hydrahive.communication.discord import ops_format as fmt
from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, discord_errors, egress_scrub, kind, parse_id, permissions,
    require_perm, resolve_moderated,
)

AUDIT_PREFIX = "HydraHive-Agent"
_FLAG_TEXT = {"locked": ("gesperrt", "entsperrt"), "pinned": ("angeheftet", "nicht mehr angeheftet")}


def audit_reason(action: str) -> str:
    return f"{AUDIT_PREFIX}: {action}"[:512]


async def _thread(scope: Scope, raw_id: object) -> discord.Thread:
    ch = await resolve_moderated(scope, raw_id)
    if kind(ch) != "thread":
        raise DiscordToolError(
            "Das ist kein Forum-Beitrag — die Beitrag-ID angeben (siehe discord_read auf das Forum).")
    return ch  # type: ignore[return-value]


def _merged_tags(thread: discord.Thread, set_tags, add_tags, remove_tags):
    """Neue Tag-Liste oder None, wenn keine Tag-Änderung gewünscht ist."""
    if set_tags is None and not add_tags and not remove_tags:
        return None
    forum = thread.parent
    if forum is None or kind(forum) != "forum":
        raise DiscordToolError("Tags gibt es nur bei Beiträgen in einem Forum.")
    tags = (fmt.resolve_tags(forum, set_tags, can_moderate=True) if set_tags is not None
            else list(thread.applied_tags))
    for tag in fmt.resolve_tags(forum, add_tags, can_moderate=True):
        if tag not in tags:
            tags.append(tag)
    drop = fmt.resolve_tags(forum, remove_tags, can_moderate=True)
    tags = [t for t in tags if t not in drop]
    if len(tags) > fmt.MAX_TAGS:
        raise DiscordToolError(f"Höchstens {fmt.MAX_TAGS} Tags pro Beitrag erlaubt.")
    if forum.flags.require_tag and not tags:
        raise DiscordToolError("Dieses Forum verlangt mindestens einen Tag pro Beitrag.")
    return tags


async def manage_thread(scope: Scope, agent_id: str, *, post_id: object, set_tags=None,
                        add_tags=None, remove_tags=None, title: str | None = None,
                        archived: bool | None = None, locked: bool | None = None,
                        pinned: bool | None = None) -> str:
    """Tags/Titel/Status eines Forum-Beitrags ändern. Nur angegebene Felder ändern sich."""
    thread = await _thread(scope, post_id)
    require_perm(thread, "manage_threads", "Threads verwalten")
    changes: dict = {}
    notes: list[str] = []
    tags = _merged_tags(thread, set_tags, add_tags, remove_tags)
    if tags is not None:
        changes["applied_tags"] = tags
        notes.append("Tags: " + (", ".join(t.name for t in tags) or "(keine)"))
    if title is not None:
        clean = egress_scrub(scope, agent_id, title.strip())
        if not clean or len(clean) > fmt.MAX_TITLE:
            raise DiscordToolError(f"Der Titel muss 1–{fmt.MAX_TITLE} Zeichen lang sein.")
        changes["name"] = clean
        notes.append(f"Titel «{clean}»")
    for key, value in (("locked", locked), ("pinned", pinned)):
        if value is not None:
            changes[key] = bool(value)
            notes.append(_FLAG_TEXT[key][0 if value else 1])
    if pinned and kind(thread.parent) != "forum":
        raise DiscordToolError("Anheften gibt es nur für Beiträge in einem Forum.")
    was_closed = bool(thread.archived)
    close = was_closed if archived is None else bool(archived)
    if archived is not None:
        notes.append("geschlossen" if archived else "geöffnet")
    if not changes and close == was_closed:
        raise DiscordToolError("Nichts zu ändern — mindestens eine Änderung angeben.")
    reason = audit_reason("; ".join(notes))
    with discord_errors("Beitrag ändern"):
        # Geschlossene Beiträge lassen sich nicht ändern: öffnen, ändern, ggf. wieder schließen.
        if was_closed and (changes or not close):
            await thread.edit(archived=False, reason=reason)
        if changes:
            await thread.edit(**changes, reason=reason)
        if close and (changes or not was_closed):
            await thread.edit(archived=True, reason=reason)
    return f"Beitrag {thread.id} geändert: " + "; ".join(notes) + "."


async def _message_channel(scope: Scope, channel_id: object):
    ch = await resolve_moderated(scope, channel_id)
    if kind(ch) == "forum":
        raise DiscordToolError(
            "Das ist das Forum selbst. Nachrichten liegen in den Beiträgen — die Beitrag-ID angeben.")
    return ch


async def pin_message(scope: Scope, *, channel_id: object, message_id: object,
                      pin: bool = True) -> str:
    ch = await _message_channel(scope, channel_id)
    perms = permissions(ch)
    if not (perms.pin_messages or perms.manage_messages):
        raise DiscordToolError("Dem Bot fehlt in diesem Kanal die Berechtigung «Nachrichten anpinnen».")
    verb = "angepinnt" if pin else "gelöst"
    with discord_errors("Anpinnen" if pin else "Lösen"):
        msg = await ch.fetch_message(parse_id(message_id, "Nachrichten-ID"))
        if pin:
            await msg.pin(reason=audit_reason("Nachricht anpinnen"))
        else:
            await msg.unpin(reason=audit_reason("Nachricht lösen"))
    return f"Nachricht {msg.id} {verb} · {msg.jump_url}"


async def delete(scope: Scope, *, channel_id: object, message_id: object = None) -> str:
    """Mit message_id: eine Nachricht löschen. Ohne: den ganzen Forum-Beitrag."""
    if message_id:
        return await _delete_message(scope, channel_id, message_id)
    thread = await resolve_moderated(scope, channel_id)
    if kind(thread) != "thread":
        raise DiscordToolError(
            "Ohne message_id wird ein ganzer Forum-Beitrag gelöscht — dafür die Beitrag-ID "
            "angeben. Kanäle und Foren werden nie gelöscht.")
    require_perm(thread, "manage_threads", "Threads verwalten")
    name, count = fmt.neutralize(thread.name), thread.message_count
    with discord_errors("Beitrag löschen"):
        await thread.delete(reason=audit_reason(f"Beitrag «{name}» löschen"))
    return f"Beitrag {thread.id} «{name}» gelöscht ({count} Antworten)."


async def _delete_message(scope: Scope, channel_id: object, message_id: object) -> str:
    ch = await _message_channel(scope, channel_id)
    with discord_errors("Nachricht löschen"):
        msg = await ch.fetch_message(parse_id(message_id, "Nachrichten-ID"))
        own = scope.bot_id is not None and msg.author.id == scope.bot_id
        if not own and not permissions(ch).manage_messages:
            raise DiscordToolError(
                "Dem Bot fehlt in diesem Kanal die Berechtigung «Nachrichten verwalten».")
        author = fmt.neutralize(getattr(msg.author, "display_name", None) or str(msg.author.id))
        size = len(msg.clean_content or "")
        await msg.delete()
    note = (" Das war die Eröffnung — der Beitrag selbst bleibt bestehen."
            if kind(ch) == "thread" and msg.id == ch.id else "")
    return (f"Nachricht {msg.id} von {author} ({fmt.ts(msg.created_at)}, {size} Zeichen) "
            f"gelöscht. Der Inhalt wird aus Sicherheitsgründen nicht wiedergegeben.{note}")
