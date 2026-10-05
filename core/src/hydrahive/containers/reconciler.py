"""Container-Reconciler: gleicht actual_state mit `incus list` ab."""
from __future__ import annotations

import asyncio
import logging

from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 4.0
#: Geprüft werden nur stabile Zustände. "starting"/"stopping" gehören dem
#: laufenden Lifecycle-Aufruf: launch() startet den Container zum Setzen des
#: Netzes intern neu, in diesem Fenster ist er kurz "nicht laufend". Früher
#: setzte der Reconciler dann error/container_not_running, und weil "error"
#: nie wieder geprüft wurde, blieb der Fehler stehen (Befund VPS 05.10.2026).
CHECKED_STATES = ("running", "error")
TRANSITIONAL_STATES = ("starting", "stopping")
#: Übergangszustände, die länger hängen (z. B. Backend-Neustart mitten im
#: Start), werden doch geprüft. launch() braucht inkl. Image-Download bis 300 s.
STALE_TRANSITION_S = 420


def _stale(updated_at: str) -> bool:
    from datetime import datetime, timezone
    try:
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() > STALE_TRANSITION_S


async def reconcile_once() -> None:
    if not incus.is_available():
        return
    try:
        running = await incus.list_running_names()
        local = cdb.list_(owner=None)
    except Exception as e:
        logger.exception("Container-Reconciler: list fehlgeschlagen: %s", e)
        return

    for c in local:
        if c.node_id != "local":
            continue
        stale = c.actual_state in TRANSITIONAL_STATES and _stale(c.updated_at)
        if c.actual_state not in CHECKED_STATES and not stale:
            continue
        is_running = c.name in running
        if is_running:
            if c.actual_state != "running" or c.last_error_code:
                cdb.update_state(c.container_id, actual="running", error_code=None, error_params=None)
        elif c.actual_state == "running" or stale:
            new = "error" if c.desired_state == "running" else "stopped"
            cdb.update_state(
                c.container_id, actual=new,
                error_code="container_not_running" if new == "error" else None,
                error_params={} if new == "error" else None,
            )


async def run_loop(stop: asyncio.Event) -> None:
    logger.info("Container-Reconciler gestartet (Intervall %.1fs)", POLL_INTERVAL_S)
    while not stop.is_set():
        await reconcile_once()
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_INTERVAL_S)
        except asyncio.TimeoutError:
            pass
    logger.info("Container-Reconciler beendet")
