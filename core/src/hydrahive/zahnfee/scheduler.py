"""Zahnfee-Scheduler — asyncio-Task der zur konfigurierten Uhrzeit den Runner startet."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run_loop(stop: asyncio.Event) -> None:
    """Läuft im Hintergrund, prüft stündlich ob Zahnfee-Zeit ist."""
    # Warte 30s nach Startup damit DB/Datamining initialisiert sind
    await asyncio.sleep(30)

    last_run_date: str = ""

    while not stop.is_set():
        try:
            from hydrahive.zahnfee import config as cfg_mod
            from hydrahive.zahnfee import storage, runner

            cfg = cfg_mod.load()
            if cfg.enabled:
                now = datetime.now(timezone.utc)
                today = storage.today_str()

                # Läuft nur einmal pro Tag zur konfigurierten Stunde
                if now.hour == cfg.run_hour and last_run_date != today:
                    existing = storage.load()
                    if not existing or existing.date != today:
                        logger.info("zahnfee: tageszeit erreicht, starte runner")
                        last_run_date = today
                        asyncio.create_task(runner.run(), name="zahnfee-runner")
        except Exception as e:
            logger.warning("zahnfee scheduler fehler: %s", e)

        # Jede Minute prüfen — minimaler Overhead
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
