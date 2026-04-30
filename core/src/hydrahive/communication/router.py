"""Eingehende Channel-Events durch den Butler und (default) durch den Master-Agent.

Der Channel-Adapter ruft `handle_incoming(event)` auf:
1. Butler bekommt das Event zuerst — wenn ein Flow matcht und eine
   `stop_default`-Action liefert (reply_fixed, agent_reply, ignore, …),
   wird der Master übersprungen.
2. Sonst geht's normal an den Master-Agent.
"""
from __future__ import annotations

import logging

from hydrahive.butler.dispatch import dispatch_for_channel
from hydrahive.communication._agent_glue import (
    NoMasterError,
    run_agent_for_event,
    run_master_for_event,
)
from hydrahive.communication.base import IncomingEvent

logger = logging.getLogger(__name__)


async def handle_incoming(event: IncomingEvent) -> str | None:
    """Verarbeitet ein eingehendes Event. Returnt die Antwort (oder None)."""
    if not event.text and not event.media_type:
        return None

    # 1. Butler-Pass
    try:
        decision = await dispatch_for_channel(
            target_username=event.target_username,
            channel=event.channel,
            text=event.text or "",
            contact_id=event.external_user_id,
            contact_label=event.sender_name,
        )
    except Exception as e:
        logger.warning("Butler-Dispatch fehlgeschlagen für '%s': %s", event.channel, e)
        decision = None

    if decision and decision.stop_default:
        # Butler hat das Event übernommen — Master skippen
        if decision.reply_text:
            return decision.reply_text
        if decision.reply_via_agent:
            try:
                return await run_agent_for_event(
                    decision.reply_via_agent, event,
                    prefix=decision.reply_prefix,
                )
            except Exception as e:
                logger.exception(
                    "Butler-Agent-Reply fehlgeschlagen (agent=%s): %s",
                    decision.reply_via_agent, e,
                )
                return None
        # ignore / queue: stoppen ohne Antwort
        return None

    # 2. Default: Master-Agent
    try:
        answer = await run_master_for_event(event)
    except NoMasterError as e:
        logger.warning("%s — Event '%s' verworfen", e, event.channel)
        return None
    except Exception as e:
        logger.exception("Channel-Run fehlgeschlagen für '%s': %s", event.channel, e)
        return None
    return answer or None
