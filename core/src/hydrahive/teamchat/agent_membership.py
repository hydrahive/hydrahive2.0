"""teamchat/agent_membership.py — Agenten-Bots in Räume zu-/wegschalten.

attach_agent: Bot-Account provisionieren, in den Raum einladen + beitreten lassen,
              DB-Zuordnung speichern. Idempotent (Re-Attach schadet nicht).
detach_agent: DB-Zuordnung entfernen, Bot best-effort aus dem Raum nehmen.

Authz (Raum-Mitgliedschaft + Agent-Besitz) liegt in der Route — hier nur Mechanik.
"""
from __future__ import annotations

import logging

import nio

from hydrahive.db import teamchat as db_teamchat
from hydrahive.teamchat.client import build_client
from hydrahive.teamchat.identity import ensure_bot_identity, ensure_identity

logger = logging.getLogger(__name__)


class AgentMembershipError(Exception):
    """Wird geworfen wenn der Bot dem Raum nicht beitreten kann."""


async def attach_agent(room_id: str, inviter_user_id: str, agent_id: str) -> None:
    """Schaltet einen Agenten in einen Raum: Bot wird eingeladen, tritt bei, DB-Eintrag.

    Der Invite-Schritt darf scheitern (Bot evtl. schon Mitglied) — maßgeblich ist,
    dass der Bot am Ende beigetreten ist. Erst danach wird die Zuordnung
    gespeichert, damit keine Geister-Zuordnung ohne Raum-Mitgliedschaft entsteht.
    """
    from hydrahive.settings import settings

    bot = await ensure_bot_identity(agent_id)
    inviter = await ensure_identity(inviter_user_id)

    inv_client = build_client(
        settings.matrix_homeserver_url,
        inviter.user_id, inviter.access_token, inviter.device_id,
    )
    try:
        inv_resp = await inv_client.room_invite(room_id, bot.user_id)
        if not isinstance(inv_resp, nio.RoomInviteResponse):
            logger.debug(
                "attach_agent: invite ergab %s (evtl. schon Mitglied) — versuche join",
                type(inv_resp).__name__,
            )
    finally:
        await inv_client.close()

    bot_client = build_client(
        settings.matrix_homeserver_url,
        bot.user_id, bot.access_token, bot.device_id,
    )
    try:
        join_resp = await bot_client.join(room_id)
        if not isinstance(join_resp, nio.JoinResponse):
            raise AgentMembershipError(
                f"Bot {bot.user_id} konnte Raum {room_id} nicht beitreten: {join_resp!r}"
            )
    finally:
        await bot_client.close()

    db_teamchat.attach_agent(room_id, agent_id, inviter_user_id)
    logger.info("attach_agent: Agent %s in Raum %s zugeschaltet", agent_id, room_id)


async def detach_agent(room_id: str, agent_id: str) -> None:
    """Schaltet einen Agenten aus einem Raum: DB-Eintrag weg, Bot verlässt den Raum.

    DB zuerst (das ist die Quelle der Wahrheit fürs Antwortverhalten); der
    Matrix-Leave ist best-effort — schlägt er fehl (Bot schon weg), wird nur geloggt.
    """
    from hydrahive.settings import settings

    db_teamchat.detach_agent(room_id, agent_id)

    bot = await ensure_bot_identity(agent_id)
    bot_client = build_client(
        settings.matrix_homeserver_url,
        bot.user_id, bot.access_token, bot.device_id,
    )
    try:
        leave_resp = await bot_client.room_leave(room_id)
        if not isinstance(leave_resp, nio.RoomLeaveResponse):
            logger.warning(
                "detach_agent: Bot %s konnte Raum %s nicht verlassen: %s",
                bot.user_id, room_id, type(leave_resp).__name__,
            )
    finally:
        await bot_client.close()
    logger.info("detach_agent: Agent %s aus Raum %s entfernt", agent_id, room_id)
