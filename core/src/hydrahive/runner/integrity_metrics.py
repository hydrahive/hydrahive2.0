"""Privacy-preserving aggregate metrics for Integrity observation metadata."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from hydrahive.db.connection import db

_MAX_ROWS = 10_000
_MAX_HOURS = 720


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def summarize_integrity(
    hours: int = 24, *, now: datetime | None = None, max_rows: int = _MAX_ROWS,
) -> dict[str, Any]:
    """Aggregate metadata only; never select message content or return identities."""
    if not 1 <= hours <= _MAX_HOURS:
        raise ValueError(f"hours must be between 1 and {_MAX_HOURS}")
    capped_rows = max(1, min(int(max_rows), _MAX_ROWS))
    until = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    since = until - timedelta(hours=hours)
    params = (_iso(since), _iso(until), '%"integrity"%')

    with db() as conn:
        candidate_rows = conn.execute(
            """SELECT COUNT(*) AS amount FROM messages
               WHERE created_at >= ? AND created_at <= ? AND metadata LIKE ?""",
            params,
        ).fetchone()["amount"]
        rows = conn.execute(
            """SELECT session_id, metadata FROM (
                   SELECT id, session_id, metadata, created_at FROM messages
                   WHERE created_at >= ? AND created_at <= ? AND metadata LIKE ?
                   ORDER BY created_at DESC, id DESC LIMIT ?
               ) ORDER BY created_at ASC, id ASC""",
            (*params, capped_rows),
        ).fetchall()

    signals: Counter[str] = Counter()
    evidence: Counter[str] = Counter()
    sessions: set[str] = set()
    previous_evidence: dict[str, set[str]] = {}
    observed = malformed = 0

    for row in rows:
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            malformed += 1
            continue
        integrity = metadata.get("integrity")
        if not isinstance(integrity, dict):
            continue
        snapshot = integrity.get("snapshot")
        raw_signals = integrity.get("signals")
        if not isinstance(snapshot, dict) or not isinstance(raw_signals, list):
            malformed += 1
            continue

        observed += 1
        session_id = str(row["session_id"])
        sessions.add(session_id)
        for signal in raw_signals:
            if isinstance(signal, dict) and isinstance(signal.get("kind"), str):
                signals[signal["kind"]] += 1

        current = {
            item for item in snapshot.get("evidence_kinds", [])
            if isinstance(item, str)
        }
        prior = previous_evidence.get(session_id, set())
        evidence.update(current - prior)
        previous_evidence[session_id] = current

    completion = signals["completion_claim"]
    unverified = signals["unverified_completion_claim"]
    return {
        "window_hours": hours,
        "since": _iso(since),
        "until": _iso(until),
        "candidate_rows": candidate_rows,
        "messages_observed": observed,
        "sessions_observed": len(sessions),
        "signal_counts": dict(sorted(signals.items())),
        "evidence_counts": dict(sorted(evidence.items())),
        "completion_claims": completion,
        "unverified_completion_claims": unverified,
        "unverified_rate": round(unverified / completion, 4) if completion else 0.0,
        "malformed_metadata": malformed,
        "truncated": candidate_rows > capped_rows,
    }
