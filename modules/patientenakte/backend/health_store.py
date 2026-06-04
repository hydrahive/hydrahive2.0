from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


def insert(
    payload: dict,
    user_id: str,
    automation_name: str | None = None,
    automation_id: str | None = None,
    session_id: str | None = None,
    period: str | None = None,
    aggregation: str | None = None,
) -> str:
    record_id = uuid7()
    # Roh-Insert UND Tages-Rollup in EINER Transaktion → schlägt der Rollup fehl,
    # wird auch der Rohsatz zurückgerollt (keine halbe Ingest-Spur).
    with db() as conn:
        conn.execute(
            """INSERT INTO health_ingest
               (id, received_at, user_id, automation_name, automation_id,
                session_id, period, aggregation, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_id, now_iso(), user_id, automation_name, automation_id,
             session_id, period, aggregation, json.dumps(payload)),
        )
        _process_payload_to_daily(payload, user_id, conn)
    return record_id


def list_recent(
    user_id: str,
    limit: int = 50,
    automation_id: str | None = None,
) -> list[dict]:
    with db() as conn:
        if automation_id:
            rows = conn.execute(
                """SELECT id, received_at, automation_name, automation_id, session_id,
                          period, aggregation
                   FROM health_ingest
                   WHERE user_id = ? AND automation_id = ?
                   ORDER BY received_at DESC LIMIT ?""",
                (user_id, automation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, received_at, automation_name, automation_id, session_id,
                          period, aggregation
                   FROM health_ingest WHERE user_id = ?
                   ORDER BY received_at DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def get_payload(record_id: str, user_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT payload FROM health_ingest WHERE id = ? AND user_id = ?",
            (record_id, user_id),
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
    values = [s.get("qty", 0) for s in samples if s.get("qty") is not None]
    if not values:
        return 0.0
    if name in _CUMULATIVE or name in _TIME_BASED:
        return sum(values)
    return sum(values) / len(values)


def _process_payload_to_daily(payload: dict, user_id: str, conn) -> None:
    """Schreibt den Tages-Rollup über die übergebene Verbindung ``conn`` (gleiche
    Transaktion wie der Roh-Insert bzw. eine eigene beim Backfill)."""
    try:
        data = payload.get("data", payload)
        metrics_list = data.get("metrics", [])
    except AttributeError:
        logger.warning(
            "health ingest: Payload nicht verarbeitbar (kein dict/metrics) — "
            "Rohsatz gespeichert, kein Tages-Rollup", exc_info=True,
        )
        return

    by_metric: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    units: dict[str, str] = {}

    for m in metrics_list:
        name = m.get("name", "")
        if not name:
            continue
        units[name] = m.get("units", "")
        for sample in m.get("data", []):
            sample_date = sample.get("date", "")[:10]
            if not sample_date:
                continue
            by_metric[name][sample_date].append(sample)

    if not by_metric:
        return

    rows = []
    for name, day_samples in by_metric.items():
        unit = units.get(name, "")
        for date, samples in day_samples.items():
            value = round(_aggregate_samples(name, samples), 1)
            rows.append((date, name, user_id, unit, value))

    conn.executemany(
        """INSERT INTO health_daily (date, metric_name, user_id, unit, value)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (date, metric_name, user_id) DO UPDATE SET
             value = CASE
               WHEN metric_name IN (
                 'step_count','active_energy_burned','basal_energy_burned',
                 'dietary_energy','distance_walking_running','flights_climbed',
                 'push_count','swimming_stroke_count',
                 'sleep_analysis','mindful_session','stand_time'
               ) THEN health_daily.value + excluded.value
               ELSE (health_daily.value + excluded.value) / 2.0
             END,
             unit = excluded.unit""",
        rows,
    )


def backfill_daily(user_id: str = "till") -> int:
    """Verarbeitet alle health_ingest Records eines Users in health_daily."""
    with db() as conn:
        rows = conn.execute(
            "SELECT payload FROM health_ingest WHERE user_id = ? ORDER BY received_at ASC",
            (user_id,),
        ).fetchall()

    count = 0
    for row in rows:
        try:
            payload = json.loads(row["payload"])
            with db() as conn:
                _process_payload_to_daily(payload, user_id, conn)
            count += 1
        except json.JSONDecodeError as e:
            logger.warning("health backfill: ungültiger JSON in Row, skip: %s", e)
            continue
        except Exception as e:
            logger.error("health backfill: Row-Verarbeitung fehlgeschlagen: %s", e, exc_info=True)
            continue
    return count


def get_metrics_summary(
    user_id: str,
    days: int = 7,
    metric: str | None = None,
) -> dict[str, Any]:
    since_date = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    with db() as conn:
        last_ingest = conn.execute(
            "SELECT received_at FROM health_ingest WHERE user_id = ? ORDER BY received_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        if metric:
            rows = conn.execute(
                """SELECT date, metric_name, unit, value FROM health_daily
                   WHERE user_id = ? AND date >= ? AND metric_name = ?
                   ORDER BY date ASC""",
                (user_id, since_date, metric),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT date, metric_name, unit, value FROM health_daily
                   WHERE user_id = ? AND date >= ?
                   ORDER BY date ASC""",
                (user_id, since_date),
            ).fetchall()

    if not rows:
        return {
            "metrics": {},
            "last_ingest": last_ingest["received_at"] if last_ingest else None,
            "period_days": days,
        }

    by_metric: dict[str, list] = defaultdict(list)
    units: dict[str, str] = {}
    for row in rows:
        by_metric[row["metric_name"]].append((row["date"], row["value"]))
        units[row["metric_name"]] = row["unit"]

    result: dict[str, dict] = {}
    for name, day_values_raw in by_metric.items():
        dates = [d for d, _ in day_values_raw]
        day_values = [v for _, v in day_values_raw]
        latest = day_values[-1]
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
            "unit": units[name],
            "days": [{"date": d, "value": round(v, 1)} for d, v in zip(dates, day_values)],
        }

    return {
        "metrics": result,
        "last_ingest": last_ingest["received_at"] if last_ingest else None,
        "period_days": days,
    }
