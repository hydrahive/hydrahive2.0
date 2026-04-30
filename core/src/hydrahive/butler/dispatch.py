"""Public Butler-API für Channel-Adapter.

`dispatch_for_channel(target_username, event)` läuft alle Flows des Users
und liefert eine `Decision` zurück, die der Channel-Router auswertet:

- `reply_text` → diesen Text über den Channel zurücksenden
- `reply_via_agent` (+ optional `prefix`) → Agent-Run mit diesem Agent
- `stop_default` ohne reply → Master-Agent NICHT aufrufen, schweigen
- alles None → Default-Verhalten (Master-Agent)

Die erste matchende Action mit `stop_default=True` gewinnt. So kann ein
User mehrere Flows haben, der erste der zugreift bestimmt die Antwort.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from hydrahive.butler import executor as bex
from hydrahive.butler.models import TriggerEvent

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    matched: bool = False
    reply_text: str | None = None
    reply_via_agent: str | None = None
    reply_prefix: str | None = None
    stop_default: bool = False


async def dispatch_for_channel(
    target_username: str,
    *,
    channel: str,
    text: str,
    contact_id: str | None = None,
    contact_label: str | None = None,
) -> Decision:
    event = TriggerEvent(
        event_type="message",
        channel=channel,
        contact_id=contact_id,
        contact_label=contact_label,
        is_known=False,
        message_text=text,
        owner=target_username,
    )
    results = await bex.dispatch_event(event, owner=target_username, dry_run=False)
    decision = Decision(matched=bool(results))
    for r in results:
        for a in r.get("actions_executed", []):
            if a.get("stop_default"):
                decision.stop_default = True
                if a.get("reply_text"):
                    decision.reply_text = a["reply_text"]
                if a.get("reply_via_agent"):
                    decision.reply_via_agent = a["reply_via_agent"]
                    decision.reply_prefix = a.get("reply_prefix")
                # Erste „stop"-Action gewinnt
                return decision
    return decision
