"""Überwachtes Polling aktiver AIG-Tasks."""
from __future__ import annotations

import logging

from hydrahive.settings import settings

from .aig_client import AigClient, AigError
from . import service

logger = logging.getLogger(__name__)
_STALE_AFTER_SECONDS = 600


async def _poll_one(row: dict) -> None:
    scan_id = row["id"]
    session_id = row.get("upstream_session_id")
    if not session_id:
        if service.is_stale(row, _STALE_AFTER_SECONDS):
            service.mark_failed(scan_id, "upstream_session_missing")
        return
    try:
        state = await AigClient().status(session_id)
        if state in {"pending", "running"}:
            service.touch_running(scan_id)
            return
        if state == "failed":
            service.mark_failed(scan_id, "upstream_scan_failed")
            return
        result = await AigClient().result(session_id)
        service.mark_completed(scan_id, result, settings.ai_security_max_result_bytes)
    except AigError as exc:
        logger.warning("AI-Security-Scan %s Polling fehlgeschlagen: %s", scan_id, exc.code)
        if service.is_stale(row, _STALE_AFTER_SECONDS):
            service.mark_failed(scan_id, exc.code)


async def poll_scans() -> None:
    """Pollt höchstens 20 Scans; ein Fehler isoliert den jeweiligen Datensatz."""
    for row in service.list_active(limit=20):
        try:
            await _poll_one(row)
        except Exception:
            logger.exception("AI-Security-Scan %s unerwartet fehlgeschlagen", row.get("id"))
