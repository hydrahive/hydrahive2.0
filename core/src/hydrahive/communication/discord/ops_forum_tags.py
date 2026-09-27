"""Tag-Liste eines freigegebenen Forums pflegen (braucht «Kanäle verwalten")."""
from __future__ import annotations

import discord

from hydrahive.communication.discord import ops_format as fmt
from hydrahive.communication.discord.ops_access import (
    DiscordToolError, Scope, discord_errors, egress_scrub, kind, require_perm, resolve_moderated,
)
from hydrahive.communication.discord.ops_moderate import audit_reason

MAX_FORUM_TAGS = 20     # Discord-Limit pro Forum
MAX_TAG_NAME = 20       # Discord-Limit pro Tag-Name
ACTIONS = ("create", "update", "delete")


def _clean_name(scope: Scope, agent_id: str, raw: str | None) -> str:
    name = egress_scrub(scope, agent_id, (raw or "").strip())
    if not name or len(name) > MAX_TAG_NAME:
        raise DiscordToolError(f"Tag-Namen müssen 1–{MAX_TAG_NAME} Zeichen lang sein.")
    return name


def _find(forum: discord.ForumChannel, name: str | None) -> discord.ForumTag:
    if not (name or "").strip():
        raise DiscordToolError("Welcher Tag? Den bestehenden Namen als name angeben.")
    return fmt.resolve_tags(forum, [name], can_moderate=True)[0]


def _duplicate(tags: list[discord.ForumTag], name: str, skip: discord.ForumTag | None = None) -> bool:
    key = fmt.norm_tag(name)
    return any(t is not skip and fmt.norm_tag(t.name) == key for t in tags)


def _emoji(value: str | None, current):
    """None = unverändert, '' = entfernen, sonst Unicode- oder Server-Emoji."""
    if value is None:
        return current
    return value.strip() or None


def _copy(tag: discord.ForumTag, *, name: str, emoji, moderated: bool) -> discord.ForumTag:
    new = discord.ForumTag(name=name, emoji=emoji, moderated=moderated)
    new.id = tag.id
    return new


async def manage(scope: Scope, agent_id: str, *, forum_id: object, action: str,
                 name: str | None = None, new_name: str | None = None,
                 emoji: str | None = None, moderated: bool | None = None) -> str:
    forum = await resolve_moderated(scope, forum_id)
    if kind(forum) != "forum":
        raise DiscordToolError("Tags gibt es nur in Foren — die Forum-ID angeben.")
    if action not in ACTIONS:
        raise DiscordToolError(f"Unbekannte Aktion '{action}' — erlaubt: {', '.join(ACTIONS)}.")
    require_perm(forum, "manage_channels", "Kanäle verwalten")
    tags = list(forum.available_tags)
    if action == "create":
        tag_name = _clean_name(scope, agent_id, name)
        if _duplicate(tags, tag_name):
            raise DiscordToolError(f"Einen Tag «{tag_name}» gibt es schon.")
        if len(tags) >= MAX_FORUM_TAGS:
            raise DiscordToolError(f"Ein Forum hat höchstens {MAX_FORUM_TAGS} Tags.")
        tags.append(discord.ForumTag(name=tag_name, emoji=_emoji(emoji, None),
                                     moderated=bool(moderated)))
        note = f"Tag «{tag_name}» angelegt"
    elif action == "update":
        old = _find(forum, name)
        tag_name = _clean_name(scope, agent_id, new_name) if new_name else old.name
        if _duplicate(tags, tag_name, skip=old):
            raise DiscordToolError(f"Einen Tag «{tag_name}» gibt es schon.")
        new = _copy(old, name=tag_name, emoji=_emoji(emoji, old.emoji),
                    moderated=old.moderated if moderated is None else bool(moderated))
        tags = [new if t is old else t for t in tags]
        note = f"Tag «{old.name}» geändert"
    else:
        old = _find(forum, name)
        tags = [t for t in tags if t is not old]
        note = f"Tag «{old.name}» entfernt (auch von allen Beiträgen)"
    with discord_errors("Tags speichern"):
        await forum.edit(available_tags=tags, reason=audit_reason(note))
    listing = ", ".join(fmt.tag_label(t) for t in tags) or "(keine)"
    return f"{note}. Tags im Forum jetzt: {listing}"
