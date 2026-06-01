import { useTranslation } from "react-i18next"
import type { MetricDay, MetricsSummary } from "./api"

const METRIC_META: Record<string, { icon: string; label: string }> = {
  step_count:               { icon: "🦶", label: "Schritte" },
  heart_rate:               { icon: "❤️", label: "Herzfrequenz" },
  sleep_analysis:           { icon: "😴", label: "Schlaf" },
  active_energy_burned:     { icon: "🔥", label: "Aktiv kcal" },
  basal_energy_burned:      { icon: "⚡", label: "Basis kcal" },
  respiratory_rate:         { icon: "🌬️", label: "Atemfrequenz" },
  blood_oxygen_saturation:  { icon: "💧", label: "SpO₂" },
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

function Sparkline({ days }: { days: MetricDay[] }) {
  if (days.length < 2) return null
  const values = days.map((d) => d.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const W = 80, H = 24
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W
    const y = H - ((v - min) / range) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(" ")
  return (
    <svg width={W} height={H} className="opacity-40">
      <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

interface Props {
  summary: MetricsSummary
}

export function MetricCards({ summary }: Props) {
  const { t } = useTranslation("health")
  const entries = Object.entries(summary.metrics)

  if (entries.length === 0) {
    return (
      <p className="text-zinc-600 text-sm text-center py-8">
        {t("no_data")}
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
            <div className="flex items-end justify-between gap-2">
              <div className={`text-xs font-mono ${trendColor(m.trend)}`}>
                {m.trend}
              </div>
              <div className={trendColor(m.trend)}>
                <Sparkline days={m.days} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
