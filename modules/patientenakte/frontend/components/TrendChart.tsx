import { useState } from "react"
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from "recharts"
import type { MetricsSummary } from "../api"

const METRIC_LABELS: Record<string, string> = {
  // Aktivität
  step_count:                        "Schritte",
  distance_walking_running:          "Distanz (Gehen/Laufen)",
  active_energy_burned:              "Aktive Kalorien",
  active_energy:                     "Aktive Kalorien",
  basal_energy_burned:               "Ruhe-Kalorien",
  apple_exercise_time:               "Trainingszeit",
  flights_climbed:                   "Treppen",
  apple_stand_hour:                  "Steh-Stunden",
  apple_stand_time:                  "Stehzeit",
  physical_effort:                   "Körperanstrengung",
  six_minute_walking_test_distance:  "6-Minuten-Gehtest",
  // Herzkreislauf
  heart_rate:                        "Herzfrequenz",
  resting_heart_rate:                "Ruheherzfrequenz",
  walking_heart_rate_average:        "Herzfrequenz (Gehen)",
  heart_rate_variability:            "Herzfrequenzvariabilität",
  blood_oxygen_saturation:           "SpO₂",
  // Atmung
  respiratory_rate:                  "Atemfrequenz",
  breathing_disturbances:            "Atemstörungen",
  // Gang & Mobilität
  walking_speed:                     "Gehgeschwindigkeit",
  walking_step_length:               "Schrittlänge",
  walking_asymmetry_percentage:      "Gangsymmetrie",
  walking_double_support_percentage: "Doppelstandphase",
  stair_speed_up:                    "Treppengeschw. (rauf)",
  stair_speed_down:                  "Treppengeschw. (runter)",
  // Umwelt & Sonstiges
  headphone_audio_exposure:          "Kopfhörer-Lautstärke",
  environmental_audio_exposure:      "Umgebungslärm",
  time_in_daylight:                  "Tageslicht",
  apple_sleeping_wrist_temperature:  "Handgelenktemp. (Schlaf)",
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
  const [selected, setSelected] = useState<string>("")
  const effectiveSelected = metricNames.includes(selected) ? selected : (metricNames[0] ?? "")

  if (metricNames.length === 0) {
    return <p className="text-zinc-600 text-sm text-center py-8">Keine Daten.</p>
  }

  const metric = summary.metrics[effectiveSelected]
  const data = (metric?.days ?? []).map((d) => ({
    date: formatDate(d.date),
    value: d.value,
  }))

  return (
    <div className="space-y-4">
      {/* Metrik-Picker */}
      <div role="group" aria-label="Metrik auswählen" className="flex flex-wrap gap-1.5">
        {metricNames.map((name) => (
          <button
            key={name}
            onClick={() => setSelected(name)}
            aria-pressed={effectiveSelected === name}
            className={`px-2.5 py-1 rounded-lg text-xs transition-colors border ${
              effectiveSelected === name
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
                width={48} /* px: enough for 4–5 digit values */
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
