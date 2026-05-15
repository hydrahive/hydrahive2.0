from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def insert(
    payload: dict,
    automation_name: str | None = None,
    automation_id: str | None = None,
    session_id: str | None = None,
    period: str | None = None,
    aggregation: str | None = None,
) -> str:
    record_id = uuid7()
    with db() as conn:
        conn.execute(
            """INSERT INTO health_ingest
               (id, received_at, automation_name, automation_id, session_id, period, aggregation, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_id, now_iso(), automation_name, automation_id,
             session_id, period, aggregation, json.dumps(payload)),
        )
    return record_id


def list_recent(limit: int = 50, automation_id: str | None = None) -> list[dict]:
    with db() as conn:
        if automation_id:
            rows = conn.execute(
                """SELECT id, received_at, automation_name, automation_id, session_id,
                          period, aggregation
                   FROM health_ingest WHERE automation_id = ?
                   ORDER BY received_at DESC LIMIT ?""",
                (automation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, received_at, automation_name, automation_id, session_id,
                          period, aggregation
                   FROM health_ingest ORDER BY received_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_payload(record_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT payload FROM health_ingest WHERE id = ?", (record_id,)
        ).fetchone()
    if not row:
        return None
    return json.loads(row["payload"])


# Kumulative Metriken: Summe pro Tag
_CUMULATIVE = {
    "step_count", "active_energy_burned", "basal_energy_burned",
    "dietary_energy", "distance_walking_running", "flights_climbed",
    "push_count", "swimming_stroke_count",
}
# Zeitbasierte Metriken: Summe in Minuten
_TIME_BASED = {"sleep_analysis", "mindful_session", "stand_time"}


def _aggregate_samples(name: str, samples: list[dict]) -> float:
    """Aggregiert Messwerte zu einem Tageswert."""
    values = [s.get("qty", 0) for s in samples if s.get("qty") is not None]
    if not values:
        return 0.0
    if name in _CUMULATIVE or name in _TIME_BASED:
        return sum(values)
    return sum(values) / len(values)


def get_metrics_summary(days: int = 7, metric: str | None = None) -> dict[str, Any]:
    """Aggregiert Metriken aus den letzten `days` Tagen."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with db() as conn:
        rows = conn.execute(
            "SELECT received_at, payload FROM health_ingest WHERE received_at >= ? ORDER BY received_at ASC",
            (since,),
        ).fetchall()

    if not rows:
        return {"metrics": {}, "last_ingest": None, "period_days": days}

    by_metric: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    units: dict[str, str] = {}
    last_ingest: str | None = None

    for row in rows:
        last_ingest = row["received_at"]
        try:
            data = json.loads(row["payload"])
            metrics_list = data.get("data", data).get("metrics", [])
        except (json.JSONDecodeError, AttributeError):
            continue
        for m in metrics_list:
            name = m.get("name", "")
            if not name:
                continue
            if metric and name != metric:
                continue
            units[name] = m.get("units", "")
            for sample in m.get("data", []):
                sample_date_raw = sample.get("date", "")
                if not sample_date_raw:
                    continue
                sample_date = sample_date_raw[:10]
                by_metric[name][sample_date].append(sample)

    result: dict[str, dict] = {}
    for name, day_samples in by_metric.items():
        dates = sorted(day_samples.keys())
        day_values = [_aggregate_samples(name, day_samples[d]) for d in dates]
        latest = day_values[-1] if day_values else 0.0
        if len(day_values) > 1:
            prev_avg = sum(day_values[:-1]) / len(day_values[:-1])
            if prev_avg > 0:
                pct = ((latest - prev_avg) / prev_avg) * 100
                trend = f"+{pct:.0f}%" if pct >= 0 else f"{pct:.0f}%"
            else:
                trend = "0%"
        else:
            trend = "0%"
        result[name] = {
            "latest": round(latest, 1),
            "trend": trend,
            "unit": units.get(name, ""),
            "days": [{"date": d, "value": round(v, 1)} for d, v in zip(dates, day_values)],
        }

    return {"metrics": result, "last_ingest": last_ingest, "period_days": days}
