"""Butler Cron-Emitter — feuert cron_fired-Flows zeitgesteuert.

Hintergrund-Loop (Minutentakt): lädt alle aktiven Flows mit cron_fired-
Trigger, parst die Cron-Expression (croniter) und feuert bei Fälligkeit ein
cron-TriggerEvent via executor.dispatch. Schließt die SPEC-Phase-2-Lücke —
der cron_fired-Trigger hatte bislang keinen Emitter.

Fälligkeit per Fenster (since, now]: jede geplante Zeit feuert genau einmal.
Kein Catch-up über Backend-Neustarts hinweg (since wird beim Start auf now
gesetzt) — verpasste Schedules während Downtime werden bewusst nicht nachgeholt.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from croniter import croniter

from hydrahive.butler import executor as bex
from hydrahive.butler import persistence as bp
from hydrahive.butler.models import Flow, Node, TriggerEvent

logger = logging.getLogger(__name__)

_STARTUP_DELAY = 20.0  # nach Start warten bis DB/Flows bereit
_TICK_INTERVAL = 60.0  # Minutentakt


def _cron_trigger(flow: Flow) -> Node | None:
    for n in flow.nodes:
        if n.type == "trigger" and n.subtype == "cron_fired":
            return n
    return None


def _due(cron_expr: str, since: datetime, now: datetime) -> bool:
    """True wenn die Cron-Expression im Fenster (since, now] mind. einmal feuert."""
    nxt = croniter(cron_expr, since).get_next(datetime)
    return since < nxt <= now


async def _tick(since: datetime, now: datetime) -> int:
    """Eine Auswertungsrunde — feuert alle im Fenster fälligen cron-Flows.

    Liefert die Anzahl gefeuerter Flows. Pro-Flow-Fehler werden isoliert
    (ein kaputter Flow bricht die anderen nicht).
    """
    fired = 0
    for flow in bp.list_flows(owner=None):
        if not flow.enabled:
            continue
        node = _cron_trigger(flow)
        if node is None:
            continue
        cron_expr = (node.params.get("cron") or "").strip()
        if not cron_expr:
            continue
        try:
            if not _due(cron_expr, since, now):
                continue
        except Exception as e:
            logger.warning(
                "butler cron: ungültige Expression in Flow %s/%s: %r (%s)",
                flow.owner, flow.flow_id, cron_expr, e,
            )
            continue
        schedule_id = (node.params.get("schedule_id") or "").strip()
        event = TriggerEvent(
            event_type="cron",
            payload={"schedule_id": schedule_id} if schedule_id else {},
            owner=flow.owner,
            timestamp=now.isoformat(),
        )
        try:
            result = await bex.dispatch(flow, event)
            fired += 1
            logger.info(
                "butler cron gefeuert: %s/%s matched=%s",
                flow.owner, flow.flow_id, result.get("matched"),
            )
        except Exception as e:
            logger.warning(
                "butler cron dispatch fehlgeschlagen %s/%s: %s",
                flow.owner, flow.flow_id, e,
            )
    return fired


async def run_loop(stop: asyncio.Event) -> None:
    """Hintergrund-Loop: alle ~60s die fälligen cron-Flows feuern."""
    try:
        await asyncio.wait_for(stop.wait(), timeout=_STARTUP_DELAY)
        return  # Stop schon während der Startup-Verzögerung
    except asyncio.TimeoutError:
        pass
    since = datetime.now(timezone.utc)
    while not stop.is_set():
        now = datetime.now(timezone.utc)
        try:
            await _tick(since, now)
        except Exception as e:
            logger.warning("butler cron scheduler fehler: %s", e)
        since = now
        try:
            await asyncio.wait_for(stop.wait(), timeout=_TICK_INTERVAL)
        except asyncio.TimeoutError:
            pass
