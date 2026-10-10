"""Admin: Datamining-Volltext pflegen.

- ``fulltext/backfill``: gekürzte Werkzeug-Ausgaben vollständig nachtragen (docs/specs/datamining-volltext-werkzeuge.md)
- ``index/sync`` + ``index/coverage``: Gesamtindex event_docs nachholen / Abdeckung (docs/specs/datamining-gesamtindex.md)
Beides läuft zusätzlich nachts mit der Zahnfee (zahnfee/scheduler.py).
"""
from __future__ import annotations

from fastapi import APIRouter

from hydrahive.api.routes._datamining_access import AdminAuth
from hydrahive.db import mirror

router = APIRouter(prefix="/api/datamining", tags=["datamining"])


@router.post("/fulltext/backfill")
async def trigger_fulltext_backfill(_auth: AdminAuth) -> dict:
    if mirror._pool is None:
        return {"ok": False, "reason": "Mirror nicht aktiv"}
    from hydrahive.db._mirror_fulltext_backfill import backfill_fulltext
    return {"ok": True, **await backfill_fulltext(mirror._pool)}


@router.post("/index/sync")
async def trigger_index_sync(_auth: AdminAuth) -> dict:
    if mirror._pool is None:
        return {"ok": False, "reason": "Mirror nicht aktiv"}
    from hydrahive.db._mirror_docs_sync import sync_docs
    return {"ok": True, **await sync_docs(mirror._pool)}


@router.get("/index/coverage")
async def get_index_coverage(_auth: AdminAuth) -> dict:
    from hydrahive.db._mirror_docs_sync import coverage
    return await coverage(mirror._pool)
