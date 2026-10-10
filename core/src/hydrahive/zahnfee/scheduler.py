"""Zahnfee-Scheduler — asyncio-Task der zur konfigurierten Uhrzeit den Runner startet."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def is_run_hour(run_hour: int, now: datetime | None = None) -> bool:
    """run_hour ist Ortszeit des Servers — so steht es in der Oberfläche
    („Uhrzeit (Stunde, 0–23)“). Vorher wurde UTC verglichen: Eingestellt 3,
    lief es um 5 Uhr (Sommerzeit) bzw. 4 Uhr (Task 8d2a29e5)."""
    local = (now or datetime.now(timezone.utc)).astimezone()
    return local.hour == run_hour


async def run_loop(stop: asyncio.Event) -> None:
    """Läuft im Hintergrund, prüft stündlich ob Zahnfee-Zeit ist."""
    # Warte 30s nach Startup damit DB/Datamining initialisiert sind
    await asyncio.sleep(30)

    last_run_date: str = ""

    while not stop.is_set():
        try:
            from hydrahive.zahnfee import config as cfg_mod
            from hydrahive.zahnfee import runner, storage

            cfg = cfg_mod.load()
            if cfg.enabled:
                today = storage.today_str()

                # Läuft nur einmal pro Tag zur konfigurierten Stunde
                if is_run_hour(cfg.run_hour) and last_run_date != today:
                    logger.info("zahnfee: tageszeit erreicht, starte runner")
                    last_run_date = today
                    asyncio.create_task(runner.run_all(), name="zahnfee-runner")
                    # Proaktiver Recall (L2): Cards aus den Sessions des Tages
                    # konsolidieren — Schlaf-Batch, reuse des Zahnfee-Tages-Ticks.
                    # Nur mit konfiguriertem Modell (sonst kein LLM-Verdichten).
                    if cfg.model:
                        from hydrahive.cards.consolidate import consolidate_recent
                        asyncio.create_task(
                            consolidate_recent(cfg.lookback_hours, cfg.model),
                            name="cards-consolidate",
                        )
                    # Datamining-Volltext pflegen (ohne LLM, idempotent): volle Werkzeug-Ausgaben +
                    # Gesamtindex event_docs – docs/specs/datamining-volltext-werkzeuge.md, datamining-gesamtindex.md
                    from hydrahive.db import mirror
                    if mirror._pool is not None:
                        asyncio.create_task(_nightly_index(mirror._pool), name="mirror-fulltext")
        except Exception as e:
            logger.warning("zahnfee scheduler fehler: %s", e)

        # Jede Minute prüfen — minimaler Overhead
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass


async def _nightly_index(pool) -> None:
    """Nacheinander: volle Werkzeug-Ausgaben nachtragen, dann Gesamtindex nachholen (beides ohne LLM, idempotent)."""
    from hydrahive.db._mirror_docs_sync import sync_docs
    from hydrahive.db._mirror_fulltext_backfill import backfill_fulltext
    try:
        await backfill_fulltext(pool)
        await sync_docs(pool)
    except Exception as e:  # noqa: BLE001 — nächtlicher Lauf darf die Zahnfee nie stoppen
        logger.warning("zahnfee: Datamining-Index-Pflege fehlgeschlagen: %s", e)
