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
