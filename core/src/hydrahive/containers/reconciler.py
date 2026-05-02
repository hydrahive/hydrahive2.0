"""Container-Reconciler: gleicht actual_state mit `incus list` ab."""
from __future__ import annotations

import asyncio
import logging

from hydrahive.containers import db as cdb
from hydrahive.containers import incus_client as incus

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 4.0
ACTIVE_STATES = ("running", "starting", "stopping")


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
        if c.actual_state not in ACTIVE_STATES:
            continue
        is_running = c.name in running
        if is_running:
            if c.actual_state != "running":
                cdb.update_state(c.container_id, actual="running")
        else:
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
