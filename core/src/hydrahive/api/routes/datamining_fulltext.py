"""Admin: gekürzte Werkzeug-Ausgaben vollständig in den Datamining-Index nachtragen.

Spec docs/specs/datamining-volltext-werkzeuge.md. Läuft zusätzlich nachts mit der Zahnfee (zahnfee/scheduler.py).
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
