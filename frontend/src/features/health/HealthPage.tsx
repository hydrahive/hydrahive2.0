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
  const [summary, setSummary] = useState<MetricsSummary | null>(null)
  const [records, setRecords] = useState<IngestRecord[] | null>(null)
  const [error, setError]     = useState<string | null>(null)
  const [days, setDays]       = useState(30)
  const [tab, setTab]         = useState<Tab>("overview")

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

      {/* Lade-Skeleton */}
      {!summary && !error && (
        <div className="space-y-3">
          <div className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />
          <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
        </div>
      )}

      {/* Tab-Inhalt */}
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
