# Health Dashboard Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three-tab layout to `/health` page — Übersicht (existing metric cards), Verlauf (line chart per metric), Schlaf (bar chart for sleep data) — all powered by the existing `healthApi.metrics()` response.

**Architecture:** All tabs share one data fetch (`healthApi.metrics(days)` + `healthApi.list()`). Tab state is local to `HealthPage`. Two new chart components (`_TrendChart`, `_SleepChart`) each receive the `MetricsSummary` already in state — no extra API calls. Recharts wraps D3 (which is already a project dependency) for declarative React charts.

**Tech Stack:** React 18, TypeScript, Recharts, Tailwind CSS. Recharts must be installed into `frontend/`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/features/health/HealthPage.tsx` | Modify | Tab navigation + route data to correct child |
| `frontend/src/features/health/_TrendChart.tsx` | Create | Metric picker + Recharts LineChart |
| `frontend/src/features/health/_SleepChart.tsx` | Create | Recharts BarChart for `sleep_analysis` |
| `frontend/src/features/health/_MetricCards.tsx` | No change | Already works as Übersicht tab content |
| `frontend/package.json` | Modify (auto) | `recharts` dependency added via npm |

---

### Task 1: Install Recharts

**Files:**
- Modify: `frontend/package.json` (via npm install)

- [ ] **Step 1: Install the package**

Run from `frontend/` directory:
```bash
cd /home/till/claudeneu/frontend
npm install recharts
```

Expected output: `added N packages` (no errors)

- [ ] **Step 2: Verify TypeScript types are included**

Recharts ships its own types — no `@types/recharts` needed. Verify:
```bash
ls node_modules/recharts/types 2>/dev/null || echo "types built-in"
grep '"types"' node_modules/recharts/package.json | head -1
```

- [ ] **Step 3: Commit**

```bash
cd /home/till/claudeneu
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(health): recharts installieren"
```

---

### Task 2: _TrendChart.tsx — Line-Chart mit Metrik-Picker

**Files:**
- Create: `frontend/src/features/health/_TrendChart.tsx`

This component receives the full `MetricsSummary`, lets the user pick a metric from a pill-button row, and renders a Recharts `LineChart` for that metric's `days` array.

- [ ] **Step 1: Create the file**

```tsx
// frontend/src/features/health/_TrendChart.tsx
import { useState } from "react"
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from "recharts"
import type { MetricsSummary } from "./api"

const METRIC_LABELS: Record<string, string> = {
  step_count: "Schritte",
  heart_rate: "Herzfrequenz",
  active_energy_burned: "Aktiv kcal",
  basal_energy_burned: "Basis kcal",
  respiratory_rate: "Atemfrequenz",
  blood_oxygen_saturation: "SpO₂",
  distance_walking_running: "Distanz",
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })
}

interface Props {
  summary: MetricsSummary
}

export function TrendChart({ summary }: Props) {
  const metricNames = Object.keys(summary.metrics).filter(
    (k) => k !== "sleep_analysis"
  )
  const [selected, setSelected] = useState<string>(metricNames[0] ?? "")

  if (metricNames.length === 0) {
    return <p className="text-zinc-600 text-sm text-center py-8">Keine Daten.</p>
  }

  const metric = summary.metrics[selected]
  const data = (metric?.days ?? []).map((d) => ({
    date: formatDate(d.date),
    value: d.value,
  }))

  return (
    <div className="space-y-4">
      {/* Metrik-Picker */}
      <div className="flex flex-wrap gap-1.5">
        {metricNames.map((name) => (
          <button
            key={name}
            onClick={() => setSelected(name)}
            className={`px-2.5 py-1 rounded-lg text-xs transition-colors border ${
              selected === name
                ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                : "text-zinc-500 hover:text-zinc-300 border-white/[6%] hover:bg-white/[4%]"
            }`}
          >
            {METRIC_LABELS[name] ?? name}
          </button>
        ))}
      </div>

      {/* Chart */}
      {data.length === 0 ? (
        <p className="text-zinc-600 text-sm text-center py-8">Keine Daten für diesen Zeitraum.</p>
      ) : (
        <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={48}
              />
              <Tooltip
                contentStyle={{
                  background: "#18181b",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "#f4f4f5",
                }}
                labelStyle={{ color: "#a1a1aa" }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#f43f5e"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#f43f5e" }}
              />
            </LineChart>
          </ResponsiveContainer>
          {metric?.unit && (
            <p className="text-[11px] text-zinc-600 mt-1 text-right">
              Einheit: {metric.unit}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep error | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/health/_TrendChart.tsx
git commit -m "feat(health): TrendChart — Recharts LineChart mit Metrik-Picker"
```

---

### Task 3: _SleepChart.tsx — Balken-Chart Schlaf

**Files:**
- Create: `frontend/src/features/health/_SleepChart.tsx`

Shows a bar chart of `sleep_analysis` minutes per day. Bars display hours (minutes / 60) for readability.

- [ ] **Step 1: Create the file**

```tsx
// frontend/src/features/health/_SleepChart.tsx
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts"
import type { MetricsSummary } from "./api"

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { value: number }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const minutes = payload[0].value
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return (
    <div className="bg-zinc-900 border border-white/[8%] rounded-lg px-3 py-2 text-xs">
      <p className="text-zinc-400">{label}</p>
      <p className="text-zinc-100 font-medium">{h}h {m}m</p>
    </div>
  )
}

interface Props {
  summary: MetricsSummary
}

export function SleepChart({ summary }: Props) {
  const sleep = summary.metrics["sleep_analysis"]

  if (!sleep || sleep.days.length === 0) {
    return (
      <p className="text-zinc-600 text-sm text-center py-8">
        Keine Schlaf-Daten für diesen Zeitraum.
      </p>
    )
  }

  const data = sleep.days.map((d) => ({
    date: formatDate(d.date),
    minutes: d.value,
  }))

  const avg = data.reduce((s, d) => s + d.minutes, 0) / data.length

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-xs text-zinc-500">
        <span>
          Durchschnitt:{" "}
          <span className="text-zinc-300 font-medium">
            {Math.floor(avg / 60)}h {Math.round(avg % 60)}m
          </span>
        </span>
        <span className="text-zinc-700">|</span>
        <span>
          Empfehlung:{" "}
          <span className="text-emerald-400 font-medium">7–9h</span>
        </span>
      </div>

      <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v: number) => `${Math.floor(v / 60)}h`}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              y={420}
              stroke="rgba(52,211,153,0.3)"
              strokeDasharray="4 4"
              label={{ value: "7h", fill: "#34d399", fontSize: 10, position: "right" }}
            />
            <Bar
              dataKey="minutes"
              fill="#6366f1"
              radius={[3, 3, 0, 0]}
              maxBarSize={32}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep error | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/health/_SleepChart.tsx
git commit -m "feat(health): SleepChart — Recharts BarChart mit Referenzlinie"
```

---

### Task 4: HealthPage.tsx — Tab-Navigation einbauen

**Files:**
- Modify: `frontend/src/features/health/HealthPage.tsx`

Replace the current single-scroll layout with a three-tab structure. The days-selector stays in the header (affects all tabs). Tab state is a local `"overview" | "trend" | "sleep"` string.

- [ ] **Step 1: Replace HealthPage.tsx completely**

```tsx
// frontend/src/features/health/HealthPage.tsx
import { useEffect, useState } from "react"
import { Activity } from "lucide-react"
import { MetricCards } from "./_MetricCards"
import { IngestList } from "./_IngestList"
import { TrendChart } from "./_TrendChart"
import { SleepChart } from "./_SleepChart"
import { healthApi, type MetricsSummary, type IngestRecord } from "./api"

type Tab = "overview" | "trend" | "sleep"

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Übersicht" },
  { id: "trend",    label: "Verlauf" },
  { id: "sleep",    label: "Schlaf" },
]

export function HealthPage() {
  const [summary, setSummary]   = useState<MetricsSummary | null>(null)
  const [records, setRecords]   = useState<IngestRecord[] | null>(null)
  const [error, setError]       = useState<string | null>(null)
  const [days, setDays]         = useState(30)
  const [tab, setTab]           = useState<Tab>("overview")

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
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
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
          {([7, 14, 30, 90] as const).map((d) => (
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

      {/* Tab-Navigation */}
      <div className="flex gap-1 border-b border-white/[6%]">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm transition-colors -mb-px border-b-2 ${
              tab === id
                ? "border-rose-500 text-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab-Inhalt */}
      {!summary && !error && (
        <div className="space-y-3">
          <div className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />
          <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
        </div>
      )}

      {summary && (
        <>
          {tab === "overview" && (
            <div className="space-y-6">
              <MetricCards summary={summary} />
              <section>
                <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
                  Ingest-Verlauf
                </h2>
                <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 overflow-hidden">
                  {records ? <IngestList records={records} /> : <div className="h-32 animate-pulse" />}
                </div>
              </section>
            </div>
          )}

          {tab === "trend" && <TrendChart summary={summary} />}

          {tab === "sleep" && <SleepChart summary={summary} />}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd /home/till/claudeneu/frontend && npx tsc --noEmit 2>&1 | grep error | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/health/HealthPage.tsx
git commit -m "feat(health): Tab-Navigation — Übersicht / Verlauf / Schlaf"
```

---

### Task 5: Deploy

**Files:** none (deploy only)

- [ ] **Step 1: Push to GitHub**

```bash
cd /home/till/claudeneu
git push origin main
```

- [ ] **Step 2: Trigger deploy on production**

```bash
echo 'gothictrustno1+-' | ssh till@192.168.3.22 "sudo -S sh -c 'touch /var/lib/hydrahive2/.update_request'"
```

- [ ] **Step 3: Verify production commit**

Poll until the new commit appears (replace `COMMIT_HASH` with the actual hash from `git log --oneline -1`):

```bash
ssh till@192.168.3.22 "until curl -s http://localhost:8001/api/health | grep -q COMMIT_HASH; do sleep 5; done && curl -s http://localhost:8001/api/health"
```

Expected: `{"status":"ok","commit":"<new hash>",...}`
