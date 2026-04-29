"""Eingehende Channel-Events durch den Master-Agent jagen.

Der Channel-Adapter ruft `handle_incoming(event)` auf. Wir kümmern uns
um den Run-Lifecycle und liefern die Antwort zurück — der Channel sendet
sie dann selbst aus.
"""
from __future__ import annotations

import logging

from hydrahive.communication._agent_glue import (
    NoMasterError,
    run_master_for_event,
)
from hydrahive.communication.base import IncomingEvent

logger = logging.getLogger(__name__)


async def handle_incoming(event: IncomingEvent) -> str | None:
    """Verarbeitet ein eingehendes Event. Returnt die Antwort (oder None bei Fehler)."""
    if not event.text and not event.media_type:
        return None
    try:
        answer = await run_master_for_event(event)
    except NoMasterError as e:
        logger.warning("%s — Event '%s' verworfen", e, event.channel)
        return None
    except Exception as e:
        logger.exception("Channel-Run fehlgeschlagen für '%s': %s", event.channel, e)
        return None
    return answer or None
