"""teamchat/agent_bridge.py — Anrede-Erkennung für zugeschaltete Agenten.

is_addressed: entscheidet synchron (kein I/O, keine LLM-Frage), ob eine
eingehende Raum-Nachricht einen bestimmten Agenten anspricht. Wird im
POST-Message-Handler aufgerufen, BEVOR ein teurer Agent-Run startet.

"mittel"-Heuristik (Till bestätigt 2026-06-03):
  - Matrix-`m.mentions` mit der Bot-MXID  → adressiert (stärkstes Signal)
  - `@name` als ganzes Wort               → adressiert
  - Name als Vokativ: ganzes Wort am Anfang ODER direkt an Komma/Doppelpunkt
  - Name beiläufig im Fließtext           → NICHT adressiert
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from hydrahive.agents import config as agent_config
from hydrahive.communication._agent_glue import run_agent_for_event
from hydrahive.communication.base import IncomingEvent
from hydrahive.db import teamchat as db_teamchat
from hydrahive.teamchat.broadcaster import room_broadcaster
from hydrahive.teamchat.client import build_client
from hydrahive.teamchat.identity import ensure_bot_identity
from hydrahive.teamchat.loop_guard import LoopGuard

logger = logging.getLogger(__name__)

# Matrix-Typing-Timeout in ms — wie lange der Indikator ohne Refresh stehen bleibt.
_TYPING_TIMEOUT_MS = 30_000

# Ein gemeinsamer Circuit-Breaker für alle Räume (room_id-getrennt intern).
_loop_guard = LoopGuard()

# Referenzen auf laufende fire-and-forget-Tasks — ohne Halten würde der GC sie
# vorzeitig einsammeln (asyncio hält nur schwache Referenzen).
_background_tasks: set[asyncio.Task] = set()


def is_addressed(
    text: str,
    agent_name: str,
    *,
    mention_mxids: list[str] | None = None,
    bot_mxid: str | None = None,
) -> bool:
    """Prüft ob *agent_name* in *text* angesprochen wird.

    Args:
        text:          Roher Nachrichtentext.
        agent_name:    Klartext-Name des Agenten (z.B. "buddy").
        mention_mxids: MXIDs aus Matrix-`m.mentions` (falls vorhanden).
        bot_mxid:      Die MXID dieses Agenten-Bots (für den m.mentions-Abgleich).
    """
    # 1. Explizite Matrix-Mention der Bot-MXID — Text egal.
    if bot_mxid and mention_mxids and bot_mxid in mention_mxids:
        return True

    name = agent_name.strip().lower()
    if not name or not text:
        return False

    lowered = text.lower()
    word = re.escape(name)

    # 2. @-Anrede als ganzes Wort: "@buddy"
    if re.search(rf"@{word}\b", lowered):
        return True

    # 3. Vokativ: Name als ganzes Wort am Anfang, vor Komma/Doppelpunkt,
    #    oder als nachgestellte Anrede nach einem Komma.
    if re.search(rf"^\s*{word}\b", lowered):
        return True
    if re.search(rf"\b{word}\s*[,:]", lowered):
        return True
    if re.search(rf",\s*{word}\b", lowered):
        return True

    return False


def schedule_response(
    room_id: str,
    sender_user_id: str,
    text: str,
    *,
    mention_mxids: list[str] | None = None,
) -> asyncio.Task:
    """Plant respond_if_addressed als fire-and-forget-Task.

    Die POST-Message-Route ruft das NACH send+broadcast, damit die HTTP-Antwort
    nicht auf den (langsamen) Agent-Run wartet.
    """
    task = asyncio.create_task(
        respond_if_addressed(room_id, sender_user_id, text, mention_mxids=mention_mxids)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def respond_if_addressed(
    room_id: str,
    sender_user_id: str,
    text: str,
    *,
    mention_mxids: list[str] | None = None,
) -> None:
    """Lässt jeden zugeschalteten, angesprochenen Agenten im Raum antworten.

    Wird vom POST-Message-Handler als fire-and-forget-Task aufgerufen, NACHDEM
    die Menschen-Nachricht gesendet und gebroadcastet wurde. Jeder Agent wird
    isoliert verarbeitet — ein Fehler reißt die Task nicht hoch.
    """
    for entry in db_teamchat.list_room_agents(room_id):
        agent_id = entry["agent_id"]
        try:
            cfg = agent_config.get(agent_id)
            if not cfg or cfg.get("status") == "disabled":
                continue
            bot = await ensure_bot_identity(agent_id)
            if not is_addressed(
                text, cfg.get("name", ""),
                mention_mxids=mention_mxids, bot_mxid=bot.user_id,
            ):
                continue
            if _loop_guard.check(room_id, is_bot=True):
                logger.warning(
                    "teamchat: LoopGuard blockt Agent %s in Raum %s", agent_id, room_id,
                )
                continue
            await _run_and_post(room_id, agent_id, cfg, bot, sender_user_id, text)
        except Exception:
            logger.exception(
                "teamchat: Agent %s in Raum %s fehlgeschlagen", agent_id, room_id,
            )


async def _run_and_post(
    room_id: str,
    agent_id: str,
    cfg: dict,
    bot,
    sender_user_id: str,
    text: str,
) -> None:
    """Triggert den Agent-Run und postet die Antwort als Bot in den Raum.

    Typing-Indikator während des (langsamen) Runs an, danach aus. Die Antwort
    ist durch run_agent_for_event bereits egress-`scrub`t. Broadcast in derselben
    Form wie die POST-Message-Route (event_id/sender/text).
    """
    from hydrahive.settings import settings

    owner = cfg.get("owner")
    if not owner:
        # Ohne Besitzer liefe die Session unter dem Absender — das wäre eine stille
        # Fehlleitung. Ein korrekt angelegter Agent hat immer einen owner.
        logger.warning("teamchat: Agent %s ohne owner — übersprungen", agent_id)
        return

    client = build_client(
        settings.matrix_homeserver_url,
        bot.user_id, bot.access_token, bot.device_id,
    )
    try:
        await client.room_typing(room_id, typing_state=True, timeout=_TYPING_TIMEOUT_MS)
        event = IncomingEvent(
            channel="matrix",
            external_user_id=room_id,
            target_username=owner,
            text=text,
            sender_name=sender_user_id,
            metadata={"is_owner": True, "is_group": True},
        )
        try:
            answer = await run_agent_for_event(agent_id, event)
        finally:
            # Typing-Indikator IMMER beenden, sonst spinnt er bis zum Homeserver-
            # Timeout (30s) weiter wenn der Run fehlschlägt.
            await client.room_typing(room_id, typing_state=False)

        if not answer.strip():
            return

        resp = await client.room_send(
            room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": answer},
        )
        event_id = getattr(resp, "event_id", None)
        if event_id is None:
            # Kein vollständiges repr der nio-Response loggen (kann Header/Token tragen).
            logger.warning("teamchat: Bot-Send fehlgeschlagen room=%s resp=%s", room_id, type(resp).__name__)
            return
        room_broadcaster.broadcast(
            room_id,
            json.dumps({"event_id": event_id, "sender": bot.user_id, "text": answer}),
        )
    finally:
        await client.close()
