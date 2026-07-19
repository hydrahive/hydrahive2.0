"""Background dead-node detection with audited health transitions."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from hydrahive.compute import audit, jobs
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


def _cutoff(now: datetime, seconds: int) -> str:
    return (now - timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _audit_rows(conn, rows, target: str) -> None:
    for row in rows:
        audit.record_in_connection(
            conn,
            actor="system:compute-monitor",
            action=f"node.{target}",
            node_id=row["node_id"],
            details={"from": row["status"], "reason": "heartbeat_timeout"},
        )


def mark_stale_nodes(*, degraded_after: int = 45, offline_after: int = 90) -> tuple[int, int]:
    if degraded_after <= 0 or offline_after <= degraded_after:
        raise ValueError("invalid stale-node thresholds")
    now = datetime.now(UTC)
    timestamp = now_iso()
    with db(immediate=True) as conn:
        offline_rows = conn.execute(
            """SELECT node_id, status FROM compute_nodes
               WHERE kind = 'agent' AND status IN ('online', 'degraded')
                 AND last_seen_at IS NOT NULL AND last_seen_at < ?""",
            (_cutoff(now, offline_after),),
        ).fetchall()
        conn.executemany(
            "UPDATE compute_nodes SET status = 'offline', updated_at = ? WHERE node_id = ?",
            ((timestamp, row["node_id"]) for row in offline_rows),
        )
        _audit_rows(conn, offline_rows, "offline")

        degraded_rows = conn.execute(
            """SELECT node_id, status FROM compute_nodes
               WHERE kind = 'agent' AND status = 'online'
                 AND last_seen_at IS NOT NULL AND last_seen_at < ?""",
            (_cutoff(now, degraded_after),),
        ).fetchall()
        conn.executemany(
            "UPDATE compute_nodes SET status = 'degraded', updated_at = ? WHERE node_id = ?",
            ((timestamp, row["node_id"]) for row in degraded_rows),
        )
        _audit_rows(conn, degraded_rows, "degraded")
    return len(degraded_rows), len(offline_rows)


async def run_loop(stop: asyncio.Event, interval: float = 15.0) -> None:
    while not stop.is_set():
        try:
            await asyncio.to_thread(mark_stale_nodes)
            await asyncio.to_thread(jobs.expire_leases)
        except Exception:
            logger.exception("compute node dead-detection failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
