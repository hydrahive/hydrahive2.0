import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { TrendChart } from "./_TrendChart"
import { healthApi, type MetricsSummary } from "./api"

const PERIODS = [7, 14, 30, 90] as const

export function AppleHealthView() {
  const { t } = useTranslation("health")
  const [summary, setSummary] = useState<MetricsSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState<number>(30)

  useEffect(() => {
    setSummary(null)
    setError(null)
    healthApi.metrics(days).then(setSummary).catch(() => setError(t("loading_data")))
  }, [days])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-zinc-300">{t("tracking.trend_title")}</h2>
        <div className="flex gap-1">
          {PERIODS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-lg text-xs transition-colors ${
                days === d
                  ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[4%]"
              }`}
            >
              {t("period_days", { days: d })}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/[4%] p-4 text-sm text-rose-400">
          {error}
        </div>
      )}

      {!summary && !error && (
        <div className="space-y-3">
          <div className="h-8 w-48 rounded-lg bg-zinc-900/50 animate-pulse" />
          <div className="h-64 rounded-xl bg-zinc-900/50 animate-pulse" />
        </div>
      )}

      {summary && <TrendChart summary={summary} />}
    </div>
  )
}
