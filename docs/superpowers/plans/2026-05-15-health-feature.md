# Health Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apple Health Daten im Frontend anzeigen (Split-View: Metric-Karten + Ingest-Liste) und Buddy per Tool (`query_health_data`) zur Auswertung befähigen.

**Architecture:** Neuer Backend-Endpunkt `/api/health-data/metrics` aggregiert gespeicherte Apple-Health-Payloads on-the-fly. Buddy-Tool ruft die DB direkt ab (kein HTTP-Roundtrip). Frontend Feature-Folder `features/health/` mit vier Komponenten, eingebunden via neuer Route `/health` und einer Box in BuddyPage.

**Tech Stack:** Python 3.12 + FastAPI (Backend), React 18 + TypeScript + Tailwind (Frontend), pytest (Tests), lucide-react (Icons)

---

## File Map

| Datei | Aktion | Zweck |
|-------|--------|-------|
| `core/src/hydrahive/db/health.py` | Modify | `get_metrics_summary()` hinzufügen |
| `core/src/hydrahive/api/routes/health_data.py` | Modify | `GET /metrics` Endpunkt |
| `core/src/hydrahive/tools/health_data.py` | Create | `query_health_data` Tool |
| `core/src/hydrahive/tools/__init__.py` | Modify | Tool registrieren |
| `core/tests/test_health_api.py` | Create | Tests Backend + DB |
| `frontend/src/features/health/api.ts` | Create | API-Client |
| `frontend/src/features/health/_MetricCards.tsx` | Create | Metriken-Karten oben |
| `frontend/src/features/health/_IngestList.tsx` | Create | Ingest-Liste unten |
| `frontend/src/features/health/HealthPage.tsx` | Create | Split-View Hauptseite |
| `frontend/src/features/health/_HealthBuddyBox.tsx` | Create | Buddy-Box mit Analyse-Buttons |
| `frontend/src/App.tsx` | Modify | Route `/health` |
| `frontend/src/shared/nav-config.ts` | Modify | Nav-Eintrag "Gesundheit" |
| `frontend/src/shared/colors.ts` | Modify | Domain-Farbe für `/health` |
| `frontend/src/i18n/locales/de/nav.json` | Modify | Label DE |
| `frontend/src/i18n/locales/en/nav.json` | Modify | Label EN |
| `frontend/src/features/buddy/BuddyPage.tsx` | Modify | `_HealthBuddyBox` einbinden |

---

## Task 1: DB-Funktion `get_metrics_summary()`

**Files:**
- Modify: `core/src/hydrahive/db/health.py`
- Create: `core/tests/test_health_api.py`

- [ ] **Schritt 1: Failing Test schreiben**

```python
# core/tests/test_health_api.py
"""Tests für Health DB + API Metrics-Endpunkt."""
from __future__ import annotations
import json
import pytest
from hydrahive.db import health as health_db


def _insert_payload(metrics: list[dict], days_ago: int = 0) -> str:
    from datetime import datetime, timezone, timedelta
    from hydrahive.db._utils import uuid7
    from hydrahive.db.connection import db
    import json as _json

    received = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    payload = {"data": {"metrics": metrics, "workouts": []}}
    record_id = uuid7()
    with db() as conn:
        conn.execute(
            """INSERT INTO health_ingest
               (id, received_at, automation_name, automation_id, session_id, period, aggregation, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_id, received, "Test", "test-id", "sess", "Default", "Default",
             _json.dumps(payload)),
        )
    return record_id


def test_get_metrics_summary_leer():
    result = health_db.get_metrics_summary(days=7)
    assert "metrics" in result
    assert "last_ingest" in result
    assert result["metrics"] == {}


def test_get_metrics_summary_schritte_summiert(setup_test_env):
    _insert_payload([
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-05-15 00:00:00 +0200", "qty": 5000}]}
    ], days_ago=0)
    _insert_payload([
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-05-15 12:00:00 +0200", "qty": 3000}]}
    ], days_ago=0)
    result = health_db.get_metrics_summary(days=7)
    step = result["metrics"].get("step_count")
    assert step is not None
    assert step["latest"] == 8000  # summiert
    assert step["unit"] == "count"


def test_get_metrics_summary_herzfrequenz_gemittelt(setup_test_env):
    _insert_payload([
        {"name": "heart_rate", "units": "bpm",
         "data": [
             {"date": "2026-05-15 08:00:00 +0200", "qty": 60},
             {"date": "2026-05-15 12:00:00 +0200", "qty": 80},
         ]}
    ], days_ago=0)
    result = health_db.get_metrics_summary(days=7)
    hr = result["metrics"].get("heart_rate")
    assert hr is not None
    assert hr["latest"] == 70  # Mittelwert
    assert hr["unit"] == "bpm"


def test_get_metrics_summary_metric_filter(setup_test_env):
    result = health_db.get_metrics_summary(days=7, metric="step_count")
    for key in result["metrics"]:
        assert key == "step_count"
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
cd /home/till/claudeneu && .venv/bin/python -m pytest core/tests/test_health_api.py::test_get_metrics_summary_leer -v
```
Erwartetes Ergebnis: `AttributeError: module 'hydrahive.db.health' has no attribute 'get_metrics_summary'`

- [ ] **Schritt 3: Implementation schreiben**

In `core/src/hydrahive/db/health.py` am Ende ergänzen:

```python
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
    """Aggregiert Metriken aus den letzten `days` Tagen.

    Returns:
        {
            "metrics": {
                "step_count": {"latest": 8432, "trend": "+12%", "unit": "count", "days": [...]},
                ...
            },
            "last_ingest": "ISO8601 | None",
            "period_days": days,
        }
    """
    from datetime import datetime, timezone, timedelta

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with db() as conn:
        rows = conn.execute(
            "SELECT received_at, payload FROM health_ingest WHERE received_at >= ? ORDER BY received_at ASC",
            (since,),
        ).fetchall()

    if not rows:
        return {"metrics": {}, "last_ingest": None, "period_days": days}

    # Sammle Samples pro Metrik pro Datum
    from collections import defaultdict
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
            date = last_ingest[:10]  # YYYY-MM-DD aus received_at
            by_metric[name][date].extend(m.get("data", []))

    # Aggregiere pro Metrik + berechne Trend
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
```

- [ ] **Schritt 4: Tests ausführen — müssen PASS**

```bash
.venv/bin/python -m pytest core/tests/test_health_api.py -k "get_metrics_summary" -v
```
Erwartetes Ergebnis: 4 passed

- [ ] **Schritt 5: Commit**

```bash
git add core/src/hydrahive/db/health.py core/tests/test_health_api.py
git commit -m "feat(health): get_metrics_summary DB-Funktion mit Aggregationslogik"
```

---

## Task 2: API-Endpunkt `GET /api/health-data/metrics`

**Files:**
- Modify: `core/src/hydrahive/api/routes/health_data.py`
- Modify: `core/tests/test_health_api.py`

- [ ] **Schritt 1: Failing Test schreiben**

In `core/tests/test_health_api.py` ergänzen:

```python
def test_metrics_endpoint_ohne_key(client):
    """Ohne Key muss 401 kommen (wenn Key konfiguriert ist)."""
    import os
    os.environ["HH_HEALTH_API_KEY"] = "testkey123"
    # cached_property zurücksetzen
    from hydrahive.settings import settings
    if "health_api_key" in settings.__dict__:
        del settings.__dict__["health_api_key"]
    r = client.get("/api/health-data/metrics")
    assert r.status_code == 401
    os.environ.pop("HH_HEALTH_API_KEY", None)
    if "health_api_key" in settings.__dict__:
        del settings.__dict__["health_api_key"]


def test_metrics_endpoint_mit_key(client):
    """Mit Key muss 200 + metrics-Struktur kommen."""
    import os
    os.environ["HH_HEALTH_API_KEY"] = "testkey123"
    from hydrahive.settings import settings
    if "health_api_key" in settings.__dict__:
        del settings.__dict__["health_api_key"]
    r = client.get("/api/health-data/metrics?key=testkey123")
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body
    assert "last_ingest" in body
    assert "period_days" in body
    os.environ.pop("HH_HEALTH_API_KEY", None)
    if "health_api_key" in settings.__dict__:
        del settings.__dict__["health_api_key"]
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
.venv/bin/python -m pytest core/tests/test_health_api.py::test_metrics_endpoint_mit_key -v
```
Erwartetes Ergebnis: 404 (Route existiert noch nicht)

- [ ] **Schritt 3: Endpunkt implementieren**

In `core/src/hydrahive/api/routes/health_data.py` am Ende vor dem letzten `get_record`-Endpoint einfügen (nach `list_data`):

```python
@router.get("/metrics")
def get_metrics(
    x_hh_health_key: Annotated[str | None, Header(alias="X-HH-Health-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    key: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=365),
    metric: str | None = Query(default=None),
) -> dict:
    _check_key(x_hh_health_key, authorization, key)
    return health_db.get_metrics_summary(days=days, metric=metric)
```

- [ ] **Schritt 4: Tests ausführen — müssen PASS**

```bash
.venv/bin/python -m pytest core/tests/test_health_api.py -v
```
Erwartetes Ergebnis: alle Tests grün

- [ ] **Schritt 5: Commit**

```bash
git add core/src/hydrahive/api/routes/health_data.py core/tests/test_health_api.py
git commit -m "feat(health): GET /api/health-data/metrics Endpunkt"
```

---

## Task 3: Buddy-Tool `query_health_data`

**Files:**
- Create: `core/src/hydrahive/tools/health_data.py`
- Modify: `core/src/hydrahive/tools/__init__.py`

- [ ] **Schritt 1: Tool-Datei erstellen**

```python
# core/src/hydrahive/tools/health_data.py
"""query_health_data — Buddy-Tool für Apple Health Auswertung."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest gespeicherte Apple Health Daten (Schritte, Herzfrequenz, Schlaf, Kalorien etc.) "
    "aus dem letzten Zeitraum aus und gibt aggregierte Metriken zurück. "
    "Nutze dieses Tool für Auswertungen und Trends der Gesundheitsdaten."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "integer",
            "description": "Zeitraum in Tagen (default 7, max 365).",
            "default": 7,
        },
        "metric": {
            "type": "string",
            "description": "Optional: Filter auf eine Metrik (z.B. step_count, heart_rate, sleep_analysis).",
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.db import health as health_db
    from hydrahive.settings import settings

    if not settings.health_api_key:
        return ToolResult.fail("Health-Daten nicht konfiguriert (HH_HEALTH_API_KEY fehlt).")

    days = max(1, min(365, int(args.get("days", 7))))
    metric = (args.get("metric") or "").strip() or None

    summary = health_db.get_metrics_summary(days=days, metric=metric)

    if not summary["metrics"]:
        return ToolResult.ok({
            "message": f"Keine Health-Daten für die letzten {days} Tage gefunden.",
            "period_days": days,
        })

    return ToolResult.ok(summary)


TOOL = Tool(
    name="query_health_data",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="personal",
)
```

- [ ] **Schritt 2: Tool registrieren**

In `core/src/hydrahive/tools/__init__.py` — Import-Block erweitern:

```python
from hydrahive.tools import (
    ask_agent,
    datamining,
    file_patch,
    file_read,
    file_write,
    fetch_url,
    health_data,        # <-- hinzufügen
    list_projects,
    list_skills,
    load_skill,
    read_memory,
    search_memory,
    send_mail,
    shell,
    todo,
    web_search,
    write_memory,
)
```

Und in der `ALL_TOOLS`-Liste (nach `fetch_url.TOOL`):

```python
        fetch_url.TOOL,
        health_data.TOOL,   # <-- hinzufügen
```

- [ ] **Schritt 3: Import-Test (kein pytest nötig)**

```bash
.venv/bin/python -c "from hydrahive.tools.health_data import TOOL; print(TOOL.name)"
```
Erwartetes Ergebnis: `query_health_data`

- [ ] **Schritt 4: Commit**

```bash
git add core/src/hydrahive/tools/health_data.py core/src/hydrahive/tools/__init__.py
git commit -m "feat(health): Buddy-Tool query_health_data"
```

---

## Task 4: Frontend API-Client

**Files:**
- Create: `frontend/src/features/health/api.ts`

- [ ] **Schritt 1: Erstellen**

```typescript
// frontend/src/features/health/api.ts
import { api } from "@/shared/api-client"

export interface MetricDay {
  date: string
  value: number
}

export interface MetricSummary {
  latest: number
  trend: string
  unit: string
  days: MetricDay[]
}

export interface MetricsSummary {
  metrics: Record<string, MetricSummary>
  last_ingest: string | null
  period_days: number
}

export interface IngestRecord {
  id: string
  received_at: string
  automation_name: string | null
  automation_id: string | null
  session_id: string | null
  period: string | null
  aggregation: string | null
}

export interface IngestRecordDetail extends IngestRecord {
  payload: Record<string, unknown>
}

export const healthApi = {
  metrics(days = 7, metric?: string): Promise<MetricsSummary> {
    const params = new URLSearchParams({ days: String(days) })
    if (metric) params.set("metric", metric)
    return api<MetricsSummary>(`/health-data/metrics?${params}`)
  },

  list(limit = 50): Promise<{ records: IngestRecord[]; count: number }> {
    return api<{ records: IngestRecord[]; count: number }>(
      `/health-data/data?limit=${limit}`
    )
  },

  detail(id: string): Promise<{ id: string; payload: Record<string, unknown> }> {
    return api<{ id: string; payload: Record<string, unknown> }>(
      `/health-data/data/${id}`
    )
  },
}
```

- [ ] **Schritt 2: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep -i health
```
Erwartetes Ergebnis: keine Fehler für health

- [ ] **Schritt 3: Commit**

```bash
git add frontend/src/features/health/api.ts
git commit -m "feat(health): Frontend API-Client"
```

---

## Task 5: `_MetricCards.tsx`

**Files:**
- Create: `frontend/src/features/health/_MetricCards.tsx`

- [ ] **Schritt 1: Erstellen**

```typescript
// frontend/src/features/health/_MetricCards.tsx
import type { MetricsSummary } from "./api"

const METRIC_META: Record<string, { icon: string; label: string }> = {
  step_count:              { icon: "🦶", label: "Schritte" },
  heart_rate:              { icon: "❤️", label: "Herzfrequenz" },
  sleep_analysis:          { icon: "😴", label: "Schlaf" },
  active_energy_burned:    { icon: "🔥", label: "Aktiv kcal" },
  basal_energy_burned:     { icon: "⚡", label: "Basis kcal" },
  respiratory_rate:        { icon: "🌬️", label: "Atemfrequenz" },
  blood_oxygen_saturation: { icon: "💧", label: "SpO₂" },
  distance_walking_running: { icon: "📍", label: "Distanz" },
}

function trendColor(trend: string): string {
  if (trend.startsWith("+")) return "text-emerald-400"
  if (trend.startsWith("-")) return "text-rose-400"
  return "text-zinc-500"
}

function formatValue(name: string, value: number, unit: string): string {
  if (name === "sleep_analysis") {
    const h = Math.floor(value / 60)
    const m = Math.round(value % 60)
    return `${h}h ${m}m`
  }
  if (unit === "%" || unit === "percent") return `${value.toFixed(1)}%`
  if (value >= 1000) return value.toLocaleString("de-DE", { maximumFractionDigits: 0 })
  return value.toLocaleString("de-DE", { maximumFractionDigits: 1 })
}

interface Props {
  summary: MetricsSummary
}

export function MetricCards({ summary }: Props) {
  const entries = Object.entries(summary.metrics)

  if (entries.length === 0) {
    return (
      <p className="text-zinc-600 text-sm text-center py-8">
        Noch keine Metriken vorhanden.
      </p>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {entries.map(([name, m]) => {
        const meta = METRIC_META[name] ?? { icon: "📊", label: name }
        return (
          <div
            key={name}
            className="rounded-xl border border-white/[6%] bg-zinc-900/60 px-4 py-3 flex flex-col gap-1"
          >
            <div className="flex items-center gap-1.5 text-xs text-zinc-500">
              <span>{meta.icon}</span>
              <span>{meta.label}</span>
            </div>
            <div className="text-xl font-semibold text-zinc-100 leading-tight">
              {formatValue(name, m.latest, m.unit)}
            </div>
            <div className={`text-xs font-mono ${trendColor(m.trend)}`}>
              {m.trend}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Schritt 2: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep -i "MetricCard\|health/_"
```
Erwartetes Ergebnis: keine Fehler

- [ ] **Schritt 3: Commit**

```bash
git add frontend/src/features/health/_MetricCards.tsx
git commit -m "feat(health): MetricCards Komponente"
```

---

## Task 6: `_IngestList.tsx`

**Files:**
- Create: `frontend/src/features/health/_IngestList.tsx`

- [ ] **Schritt 1: Erstellen**

```typescript
// frontend/src/features/health/_IngestList.tsx
import { useState } from "react"
import { ChevronDown, ChevronRight, Package } from "lucide-react"
import type { IngestRecord } from "./api"
import { healthApi } from "./api"

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("de-DE", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

function MetricRow({ name, data }: { name: string; data: unknown[] }) {
  return (
    <div className="text-xs text-zinc-400 flex items-center gap-2 py-0.5">
      <span className="text-zinc-600 w-40 truncate font-mono">{name}</span>
      <span>{Array.isArray(data) ? `${data.length} Messwerte` : "—"}</span>
    </div>
  )
}

function RecordDetail({ id }: { id: string }) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  useState(() => {
    setLoading(true)
    healthApi.detail(id)
      .then((r) => setPayload(r.payload))
      .catch(() => setPayload(null))
      .finally(() => setLoading(false))
  })

  if (loading) return <div className="text-xs text-zinc-600 py-2 pl-4">Lade…</div>
  if (!payload) return null

  const data = (payload.data ?? payload) as Record<string, unknown>
  const metrics = (data.metrics ?? []) as Array<{ name: string; data: unknown[] }>
  const workouts = (data.workouts ?? []) as unknown[]

  return (
    <div className="pl-4 pt-1 pb-2 border-l border-white/[6%] ml-2 mt-1">
      {metrics.map((m) => (
        <MetricRow key={m.name} name={m.name} data={m.data} />
      ))}
      {workouts.length > 0 && (
        <div className="text-xs text-zinc-500 mt-1">{workouts.length} Workout(s)</div>
      )}
    </div>
  )
}

interface Props {
  records: IngestRecord[]
}

export function IngestList({ records }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (records.length === 0) {
    return (
      <p className="text-zinc-600 text-sm text-center py-8">
        Noch keine Daten empfangen.
      </p>
    )
  }

  return (
    <div className="divide-y divide-white/[4%]">
      {records.map((r) => {
        const open = expanded === r.id
        return (
          <div key={r.id}>
            <button
              onClick={() => setExpanded(open ? null : r.id)}
              className="w-full flex items-center gap-2 px-2 py-2.5 hover:bg-white/[2%] transition-colors text-left"
            >
              {open ? (
                <ChevronDown size={14} className="text-zinc-500 shrink-0" />
              ) : (
                <ChevronRight size={14} className="text-zinc-500 shrink-0" />
              )}
              <Package size={13} className="text-zinc-600 shrink-0" />
              <span className="text-sm text-zinc-300">{formatDate(r.received_at)}</span>
              {r.automation_name && (
                <span className="text-xs text-zinc-600 truncate ml-auto">
                  {r.automation_name}
                </span>
              )}
            </button>
            {open && <RecordDetail id={r.id} />}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Schritt 2: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep -i "IngestList\|health/_"
```
Erwartetes Ergebnis: keine Fehler

- [ ] **Schritt 3: Commit**

```bash
git add frontend/src/features/health/_IngestList.tsx
git commit -m "feat(health): IngestList Komponente"
```

---

## Task 7: `HealthPage.tsx`

**Files:**
- Create: `frontend/src/features/health/HealthPage.tsx`

- [ ] **Schritt 1: Erstellen**

```typescript
// frontend/src/features/health/HealthPage.tsx
import { useEffect, useState } from "react"
import { Activity } from "lucide-react"
import { MetricCards } from "./_MetricCards"
import { IngestList } from "./_IngestList"
import { healthApi, type MetricsSummary, type IngestRecord } from "./api"

export function HealthPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null)
  const [records, setRecords] = useState<IngestRecord[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(7)

  useEffect(() => {
    setSummary(null)
    Promise.all([
      healthApi.metrics(days),
      healthApi.list(100),
    ])
      .then(([s, l]) => {
        setSummary(s)
        setRecords(l.records)
      })
      .catch(() => setError("Daten konnten nicht geladen werden."))
  }, [days])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <Activity size={18} className="text-rose-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">Gesundheit</h1>
            <p className="text-xs text-zinc-500">Apple Health Auto Export</p>
          </div>
        </div>
        <div className="flex gap-1">
          {([7, 14, 30] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-lg text-xs transition-colors ${
                days === d
                  ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[4%]"
              }`}
            >
              {d}T
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/[4%] p-4 text-sm text-rose-400">
          {error}
        </div>
      )}

      {/* Metriken-Karten */}
      <section>
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
          Letzte {days} Tage
        </h2>
        {summary ? (
          <MetricCards summary={summary} />
        ) : (
          !error && <div className="h-24 rounded-xl bg-zinc-900/50 animate-pulse" />
        )}
      </section>

      {/* Ingest-Liste */}
      <section>
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
          Ingest-Verlauf
        </h2>
        <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 overflow-hidden">
          {records ? (
            <IngestList records={records} />
          ) : (
            !error && <div className="h-32 animate-pulse" />
          )}
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Schritt 2: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep -i "HealthPage\|health/"
```
Erwartetes Ergebnis: keine Fehler

- [ ] **Schritt 3: Commit**

```bash
git add frontend/src/features/health/HealthPage.tsx
git commit -m "feat(health): HealthPage Split-View"
```

---

## Task 8: `_HealthBuddyBox.tsx`

**Files:**
- Create: `frontend/src/features/health/_HealthBuddyBox.tsx`

- [ ] **Schritt 1: Erstellen**

```typescript
// frontend/src/features/health/_HealthBuddyBox.tsx
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Activity } from "lucide-react"
import { healthApi } from "./api"

const QUICK_PROMPTS = [
  { label: "📊 Tagesauswertung", prompt: "Werte meinen heutigen Gesundheitstag aus. Schau dir Schritte, Herzfrequenz, Schlaf und Kalorien an." },
  { label: "📈 Wochentrend",     prompt: "Analysiere meinen Gesundheitstrend der letzten 7 Tage. Gibt es Muster oder Auffälligkeiten?" },
  { label: "😴 Schlafqualität",  prompt: "Wie war meine Schlafqualität diese Woche? Gibt es Optimierungspotenzial?" },
]

interface Props {
  onPrompt: (text: string) => void
}

export function HealthBuddyBox({ onPrompt }: Props) {
  const [lastIngest, setLastIngest] = useState<string | null>(null)

  useEffect(() => {
    healthApi.metrics(1)
      .then((s) => setLastIngest(s.last_ingest))
      .catch(() => {})
  }, [])

  const formattedDate = lastIngest
    ? new Date(lastIngest).toLocaleString("de-DE", {
        day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
      })
    : null

  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-zinc-950/90 shadow-xl overflow-hidden w-60">
      <div className="px-4 py-3 border-b border-white/[6%] bg-black/20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-rose-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Gesundheit</span>
        </div>
        <Link to="/health" className="text-[10px] text-zinc-600 hover:text-zinc-400 transition-colors">
          → /health
        </Link>
      </div>
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${formattedDate ? "bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]" : "bg-zinc-600"}`} />
          <span className="text-[11px] text-zinc-500">
            {formattedDate ? `${formattedDate} · aktiv` : "Keine Daten"}
          </span>
        </div>
        <div className="flex flex-col gap-1.5">
          {QUICK_PROMPTS.map(({ label, prompt }) => (
            <button
              key={label}
              onClick={() => onPrompt(prompt)}
              className="text-left text-xs px-2.5 py-1.5 rounded-lg border border-white/[6%] hover:border-rose-500/30 hover:bg-rose-500/[3%] text-zinc-400 hover:text-zinc-300 transition-all"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Schritt 2: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep -i "BuddyBox\|health/"
```
Erwartetes Ergebnis: keine Fehler

- [ ] **Schritt 3: Commit**

```bash
git add frontend/src/features/health/_HealthBuddyBox.tsx
git commit -m "feat(health): HealthBuddyBox für BuddyPage"
```

---

## Task 9: Routing, Navigation, i18n

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/shared/nav-config.ts`
- Modify: `frontend/src/shared/colors.ts`
- Modify: `frontend/src/i18n/locales/de/nav.json`
- Modify: `frontend/src/i18n/locales/en/nav.json`

- [ ] **Schritt 1: Route in `App.tsx` eintragen**

In `App.tsx` den Import und die Route ergänzen. Suche den Block mit den bestehenden Imports der Pages und füge hinzu:

```typescript
import { HealthPage } from "@/features/health/HealthPage"
```

In der Route-Konfiguration (nach der `dashboard`-Route):

```typescript
<Route path="health" element={<HealthPage />} />
```

- [ ] **Schritt 2: Nav-Eintrag in `nav-config.ts`**

```typescript
// Import-Zeile ergänzen (Activity ist bereits in lucide-react):
import { Activity, BrainCircuit, ... } from "lucide-react"

// NAV_ITEMS — nach dem Dashboard-Eintrag einfügen:
{ path: "/health", icon: Activity, labelKey: "health" },
```

- [ ] **Schritt 3: Domain-Farbe in `colors.ts`**

In `DOMAIN_COLORS` ergänzen:

```typescript
"/health": "rose",
```

- [ ] **Schritt 4: i18n DE**

In `frontend/src/i18n/locales/de/nav.json` unter `"items"`:

```json
"health": "Gesundheit",
```

- [ ] **Schritt 5: i18n EN**

In `frontend/src/i18n/locales/en/nav.json` unter `"items"`:

```json
"health": "Health",
```

- [ ] **Schritt 6: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | head -20
```
Erwartetes Ergebnis: 0 Fehler

- [ ] **Schritt 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/shared/nav-config.ts frontend/src/shared/colors.ts \
        frontend/src/i18n/locales/de/nav.json frontend/src/i18n/locales/en/nav.json
git commit -m "feat(health): Route, Nav-Eintrag, i18n"
```

---

## Task 10: BuddyPage-Integration + Deploy

**Files:**
- Modify: `frontend/src/features/buddy/BuddyPage.tsx`

- [ ] **Schritt 1: Import hinzufügen**

In `frontend/src/features/buddy/BuddyPage.tsx`:

```typescript
import { HealthBuddyBox } from "@/features/health/_HealthBuddyBox"
```

- [ ] **Schritt 2: Box einbinden**

In `BuddyPage.tsx` nach dem Block mit `<BuddyExtensionsPanel />` (Zeile ~200) einfügen:

```typescript
<div className="hidden xl:block pt-0 shrink-0">
  <HealthBuddyBox onPrompt={(text) => handleSend(text)} />
</div>
```

`handleSend(text: string)` ist die bestehende Funktion ab Zeile 54, die auch die CmdPills nutzen.

- [ ] **Schritt 3: Finale TypeScript-Prüfung**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit
```
Erwartetes Ergebnis: 0 Fehler

- [ ] **Schritt 4: Backend-Tests nochmal komplett**

```bash
cd /home/till/claudeneu && .venv/bin/python -m pytest core/tests/test_health_api.py -v
```
Erwartetes Ergebnis: alle grün

- [ ] **Schritt 5: Commit + Push**

```bash
git add frontend/src/features/buddy/BuddyPage.tsx
git commit -m "feat(health): HealthBuddyBox in BuddyPage integriert"
git push origin main
```

- [ ] **Schritt 6: Deployment**

Auf Produktionsserver: `git pull` + Service-Neustart. Danach:

- `/health` im Browser öffnen → Metriken-Karten und Ingest-Liste erscheinen
- In Buddy-Seite: HealthBuddyBox sichtbar, Buttons senden Prompt
- Buddy-Tool `query_health_data` in den Tool-Settings aktivieren
