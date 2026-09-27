"""Zugriff der Agenten-Tools auf Discord: eigener Bot-Client + Kanal-Freigabe.

Freigabemodell (docs/specs/discord-agent-tools.md, Variante B):
- `DiscordConfig.tool_channel_ids` ist die einzige Freigabe-Quelle; leer = nichts.
- Threads/Forum-Beiträge erben die Freigabe ihres Eltern-Kanals.
- Jeder User nutzt ausschließlich seinen eigenen Bot-Client.

Alle Fehler, die der Agent sehen soll, werden als `DiscordToolError` mit einer
verständlichen deutschen Meldung geworfen — die Tool-Hüllen machen daraus ein
`ToolResult.fail`.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Iterator, Union

import discord

from hydrahive.communication.discord import config as dc_config

# Kein @everyone/@here, keine Rollen-Pings, kein Ping beim Antworten.
# User-Erwähnungen (<@id>) bleiben erlaubt — gezieltes Ansprechen ist gewollt.
NO_MASS_PINGS = discord.AllowedMentions(everyone=False, roles=False, users=True,
                                        replied_user=False)

ToolChannel = Union[discord.TextChannel, discord.ForumChannel, discord.Thread]

_TEXT_TYPES = {discord.ChannelType.text: "text", discord.ChannelType.news: "news"}
_THREAD_TYPES = {discord.ChannelType.public_thread, discord.ChannelType.private_thread,
                 discord.ChannelType.news_thread}

_NOT_ALLOWED = ("Kanal {cid} ist für Agenten-Werkzeuge nicht freigegeben (oder existiert "
                "nicht). Freigegebene Kanäle zeigt discord_channels.")


class DiscordToolError(Exception):
    """Für den Agenten bestimmte Fehlermeldung."""


@dataclass(frozen=True)
class Scope:
    username: str
    client: discord.Client
    cfg: dc_config.DiscordConfig

    @property
    def allowed(self) -> frozenset[str]:
        return frozenset(self.cfg.tool_channel_ids)

    @property
    def bot_id(self) -> int | None:
        return self.client.user.id if self.client.user else None


def connected_client(username: str) -> discord.Client:
    """Verbundener Bot-Client des Users oder DiscordToolError."""
    from hydrahive.communication import get

    adapter = get("discord")
    if adapter is None or not hasattr(adapter, "client_for"):
        raise DiscordToolError("Discord ist auf diesem Server deaktiviert.")
    client = adapter.client_for(username)
    if client is None:
        raise DiscordToolError(
            "Dein Discord-Bot ist nicht verbunden — unter Kommunikation → Discord "
            "auf «Verbinden» klicken.")
    return client


def open_scope(username: str) -> Scope:
    cfg = dc_config.load(username)
    if not cfg.tool_channel_ids:
        raise DiscordToolError(
            "Es sind keine Discord-Kanäle für Agenten-Werkzeuge freigegeben — unter "
            "Kommunikation → Discord → «Kanäle für Agenten-Werkzeuge» auswählen.")
    return Scope(username=username, client=connected_client(username), cfg=cfg)


def parse_id(raw: object, what: str = "ID") -> int:
    s = str(raw or "").strip()
    if not s.isdigit():
        raise DiscordToolError(f"Ungültige {what} '{s}' — erwartet wird eine Discord-ID aus Ziffern.")
    return int(s)


def kind(channel: object) -> str | None:
    """'text' | 'news' | 'forum' | 'thread' | None (nicht unterstützt).
    Über `channel.type` statt isinstance — so auch mit Test-Doubles prüfbar."""
    ctype = getattr(channel, "type", None)
    if ctype in _TEXT_TYPES:
        return _TEXT_TYPES[ctype]
    if ctype == discord.ChannelType.forum:
        return "forum"
    if ctype in _THREAD_TYPES:
        return "thread"
    return None


def is_allowed(scope: Scope, channel: object) -> bool:
    cid = str(getattr(channel, "id", ""))
    if cid in scope.allowed:
        return True
    if kind(channel) == "thread":
        return str(getattr(channel, "parent_id", "")) in scope.allowed
    return False


async def fetch_any(client: discord.Client, cid: int) -> object | None:
    """Kanal aus Cache oder per API; None wenn unbekannt/kein Zugriff."""
    ch = client.get_channel(cid)
    if ch is not None:
        return ch
    try:
        return await client.fetch_channel(cid)
    except (discord.NotFound, discord.Forbidden, discord.InvalidData):
        return None


async def resolve_channel(scope: Scope, raw_id: object) -> ToolChannel:
    """Freigegebenen Text-/Forum-Kanal bzw. Thread liefern — sonst Fehler.

    Nicht existent und nicht freigegeben ergeben dieselbe Meldung, damit ein
    Agent über fremde IDs nichts erfährt."""
    cid = parse_id(raw_id, "Kanal-ID")
    ch = await fetch_any(scope.client, cid)
    if ch is None or not is_allowed(scope, ch):
        raise DiscordToolError(_NOT_ALLOWED.format(cid=cid))
    if kind(ch) is None:
        raise DiscordToolError(
            f"Kanal {cid} hat einen nicht unterstützten Typ ({getattr(ch, 'type', '?')}) — "
            "unterstützt sind Text-, Ankündigungs- und Forum-Kanäle.")
    return ch  # type: ignore[return-value]


def permissions(channel: ToolChannel) -> discord.Permissions:
    return channel.permissions_for(channel.guild.me)


@contextlib.contextmanager
def discord_errors(action: str) -> Iterator[None]:
    """Discord-API-Fehler in verständliche Agenten-Meldungen übersetzen."""
    try:
        yield
    except DiscordToolError:
        raise
    except discord.Forbidden as e:
        raise DiscordToolError(
            f"{action}: Dem Bot fehlt die Berechtigung dafür (Discord: {e.text or e.status}).") from e
    except discord.NotFound as e:
        raise DiscordToolError(f"{action}: nicht gefunden (Discord: {e.text or e.status}).") from e
    except discord.HTTPException as e:
        raise DiscordToolError(f"{action}: Discord-Fehler {e.status} — {e.text}") from e
