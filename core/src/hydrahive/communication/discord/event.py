"""Eingehende Discord-Nachricht → IncomingEvent.

Session-Schlüssel (external_user_id):
- DM: die DM-Kanal-ID (ein Gespräch pro Person).
- Server-Kanal: "<kanal>:<autor>" — jeder Autor bekommt eine eigene Session.
  Vorher teilten sich alle Nutzer eines Kanals Verlauf und Kontext des Bots
  (inkl. Tool-Ergebnissen, die für den Besitzer gedacht waren).

is_group/is_owner steuern die Sender-Rahmung in `_agent_glue`:
Server-Kanal = Gruppen-Chat; eingetragene Besitzer-IDs = vertrauenswürdig.
"""
from __future__ import annotations

from hydrahive.communication.base import IncomingEvent
from hydrahive.communication.discord.config import DiscordConfig


def build_event(
    *,
    cfg: DiscordConfig,
    username: str,
    author_id: str,
    author_name: str | None,
    channel_id: str,
    guild_id: str | None,
    is_dm: bool,
    text: str,
) -> IncomingEvent:
    external_user_id = channel_id if is_dm else f"{channel_id}:{author_id}"
    return IncomingEvent(
        channel="discord",
        external_user_id=external_user_id,
        target_username=username,
        text=text,
        sender_name=author_name,
        metadata={
            "author_id": author_id,
            "channel_id": channel_id,
            "is_dm": is_dm,
            "is_group": not is_dm,
            "is_owner": author_id in cfg.owner_user_ids,
            "guild_id": guild_id,
        },
    )
