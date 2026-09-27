"""Schreibende Discord-Operationen der Agenten-Tools.

Jeder ausgehende Text läuft durch `_egress_scrub` (System-Secrets, Agent-Secrets
und der eigene Bot-Token) und wird mit `NO_MASS_PINGS` gesendet.
"""
from __future__ import annotations

import discord

from hydrahive.communication.discord import ops_format as fmt
from hydrahive.communication.discord.ops_access import (
    NO_MASS_PINGS, DiscordToolError, Scope, discord_errors, kind, parse_id, permissions,
    resolve_channel,
)


def _egress_scrub(scope: Scope, agent_id: str, text: str) -> str:
    from hydrahive.credentials import redaction
    secrets = redaction.secret_values() | redaction.agent_secret_values(agent_id)
    if scope.cfg.bot_token:
        secrets.add(scope.cfg.bot_token)
    return redaction.scrub(text, secrets)


def _check_thread_writable(thread: discord.Thread) -> None:
    perms = permissions(thread)
    if thread.locked and not perms.manage_threads:
        raise DiscordToolError(f"Beitrag {thread.id} ist gesperrt — Antworten nicht möglich.")
    if not perms.send_messages_in_threads:
        raise DiscordToolError("Dem Bot fehlt die Berechtigung «Nachrichten in Threads senden».")


async def _send_chunks(target: discord.abc.Messageable, chunks: list[str],
                       reference: discord.PartialMessage | None = None) -> list[discord.Message]:
    sent: list[discord.Message] = []
    for i, chunk in enumerate(chunks):
        ref = reference if i == 0 else None
        kwargs = {"reference": ref, "mention_author": False} if ref is not None else {}
        sent.append(await target.send(chunk, allowed_mentions=NO_MASS_PINGS, **kwargs))
    return sent


def _summary(verb: str, msgs: list[discord.Message]) -> str:
    ids = ", ".join(str(m.id) for m in msgs)
    parts = f" (auf {len(msgs)} Nachrichten verteilt)" if len(msgs) > 1 else ""
    return f"{verb}{parts}. Nachrichten-ID: {ids} · {msgs[0].jump_url}"


async def post(scope: Scope, agent_id: str, *, channel_id: object, text: str,
               title: str | None = None, tags: list[str] | None = None) -> str:
    """Textkanal → Nachricht; Forum → neuer Beitrag (Titel Pflicht)."""
    ch = await resolve_channel(scope, channel_id)
    k = kind(ch)
    chunks = fmt.split_message(_egress_scrub(scope, agent_id, text))
    if k == "forum":
        return await _create_forum_post(scope, agent_id, ch, chunks, title, tags)
    if title or tags:
        raise DiscordToolError("title/tags gibt es nur beim Anlegen eines Beitrags in einem Forum.")
    if k == "thread":
        _check_thread_writable(ch)
    elif not permissions(ch).send_messages:
        raise DiscordToolError("Dem Bot fehlt in diesem Kanal die Berechtigung «Nachrichten senden».")
    with discord_errors("Posten"):
        sent = await _send_chunks(ch, chunks)
    return _summary(f"Gepostet in #{ch.name}", sent)


async def _create_forum_post(scope: Scope, agent_id: str, forum: discord.ForumChannel,
                             chunks: list[str], title: str | None,
                             tags: list[str] | None) -> str:
    title = _egress_scrub(scope, agent_id, (title or "").strip())
    if not title:
        raise DiscordToolError("Für einen neuen Forum-Beitrag ist ein Titel (title) Pflicht.")
    if len(title) > fmt.MAX_TITLE:
        raise DiscordToolError(f"Titel zu lang ({len(title)} Zeichen, max. {fmt.MAX_TITLE}).")
    perms = permissions(forum)
    if not perms.send_messages:
        raise DiscordToolError("Dem Bot fehlt in diesem Forum die Berechtigung, Beiträge zu erstellen.")
    applied = fmt.resolve_tags(forum, tags, can_moderate=perms.manage_threads)
    if forum.flags.require_tag and not applied:
        valid = ", ".join(fmt.tag_label(t) for t in forum.available_tags)
        raise DiscordToolError(f"Dieses Forum verlangt mindestens einen Tag. Verfügbar: {valid}")
    with discord_errors("Beitrag anlegen"):
        created = await forum.create_thread(
            name=title, content=chunks[0], applied_tags=applied,
            allowed_mentions=NO_MASS_PINGS)
        sent = [created.message] + await _send_chunks(created.thread, chunks[1:])
    tag_txt = f" mit Tags {', '.join(t.name for t in applied)}" if applied else ""
    return (f"Forum-Beitrag «{title}» angelegt{tag_txt}. Beitrag-ID (für discord_reply/"
            f"discord_read): {created.thread.id}. " + _summary("Eröffnung gesendet", sent))


async def reply(scope: Scope, agent_id: str, *, channel_id: object, text: str,
                reply_to: object = None) -> str:
    """Antwort in einem Forum-Beitrag/Thread oder Textkanal."""
    ch = await resolve_channel(scope, channel_id)
    k = kind(ch)
    if k == "forum":
        raise DiscordToolError(
            "Das ist das Forum selbst. Zum Antworten die Beitrag-ID angeben (siehe "
            "discord_read auf das Forum); für einen neuen Beitrag discord_post nutzen.")
    if k == "thread":
        _check_thread_writable(ch)
    elif not permissions(ch).send_messages:
        raise DiscordToolError("Dem Bot fehlt in diesem Kanal die Berechtigung «Nachrichten senden».")
    chunks = fmt.split_message(_egress_scrub(scope, agent_id, text))
    reference = None
    with discord_errors("Antworten"):
        if reply_to:
            reference = await ch.fetch_message(parse_id(reply_to, "reply_to-ID"))
        sent = await _send_chunks(ch, chunks, reference=reference)
    return _summary(f"Antwort in «{ch.name}» gesendet", sent)


async def edit(scope: Scope, agent_id: str, *, channel_id: object, message_id: object,
               text: str) -> str:
    """Eigene Nachricht des Bots bearbeiten (fremde werden abgelehnt)."""
    ch = await resolve_channel(scope, channel_id)
    if kind(ch) == "forum":
        raise DiscordToolError(
            "Nachrichten liegen in den Beiträgen — als channel_id die Beitrag-ID angeben "
            "(bei der Eröffnung eines Beitrags ist message_id = Beitrag-ID).")
    new_text = _egress_scrub(scope, agent_id, (text or "").strip())
    if not new_text:
        raise DiscordToolError("Der neue Text ist leer.")
    if len(new_text) > fmt.MAX_MESSAGE:
        raise DiscordToolError(
            f"Neuer Text zu lang ({len(new_text)} Zeichen, max. {fmt.MAX_MESSAGE} pro Nachricht).")
    with discord_errors("Bearbeiten"):
        msg = await ch.fetch_message(parse_id(message_id, "Nachrichten-ID"))
        if scope.bot_id is None or msg.author.id != scope.bot_id:
            raise DiscordToolError(
                "Das ist keine Nachricht des Bots — bearbeitet werden können nur eigene Nachrichten.")
        if kind(ch) == "thread" and ch.locked and not permissions(ch).manage_threads:
            raise DiscordToolError(f"Beitrag {ch.id} ist gesperrt — Bearbeiten nicht möglich.")
        edited = await msg.edit(content=new_text, allowed_mentions=NO_MASS_PINGS)
    return f"Nachricht {edited.id} bearbeitet · {edited.jump_url}"
