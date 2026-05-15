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
