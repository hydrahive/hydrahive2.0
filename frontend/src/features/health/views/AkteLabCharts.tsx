import { useEffect, useState } from "react"
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts"
import { akteApi, type AkteRecord } from "../api"
import { AkteEntryModal } from "../components/AkteEntryModal"

interface Props {
  parameterFilter?: string  // show only this parameter
}

interface LabSeries {
  parameter: string
  data: { date: string; wert: number; flag: string }[]
  refLow?: number
  refHigh?: number
  unit: string
}

// Referenzbereiche (hardcoded — Iteration 2: aus Entität extrahieren)
const REFERENCE_RANGES: Record<string, [number, number, string]> = {
  HbA1c:           [4,    6,    "%"],
  "HbA1c (%)":     [4,    6,    "%"],
  eGFR:            [90,   999,  "mL/min"],
  "GPT (ALAT)":    [0,    40,   "U/L"],
  "GOT (ASAT)":    [0,    40,   "U/L"],
  Gesamtcholesterin: [0,  200,   "mg/dL"],
  "LDL-Cholesterin": [0, 116,   "mg/dL"],
  "HDL-Cholesterin": [40, 999,  "mg/dL"],
  Triglyceride:    [0,    150,  "mg/dL"],
  Nüchternglukose: [70,   100,  "mg/dL"],
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { value: number; payload: { flag: string } }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const val = payload[0].value
  const flag = payload[0]?.payload?.flag ?? "normal"
  return (
    <div className="bg-zinc-900 border border-white/[8%] rounded-lg px-3 py-2 text-xs">
      <p className="text-zinc-400">{label}</p>
      <p className={`font-medium ${flag === "high" ? "text-red-400" : flag === "low" ? "text-orange-400" : "text-emerald-400"}`}>
        {val} {""}
      </p>
      <p className="text-zinc-600 capitalize">{flag}</p>
    </div>
  )
}

function getFlag(wert: number, refLow: number, refHigh: number): string {
  if (wert > refHigh) return "high"
  if (wert < refLow) return "low"
  return "normal"
}

export function AkteLabCharts({ parameterFilter }: Props) {
  const [series, setSeries] = useState<LabSeries[] | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    akteApi.listEntity("observations")
      .then((records) => {
        // Nur numerische Observations mit parameter-Feld
        const numerics = records.filter((r: AkteRecord) => {
          const w = (r.record as any).wert
          return typeof w === "number" && (r.record as any).parameter
        })

        // Gruppiere nach parameter
        const byParam: Record<string, AkteRecord[]> = {}
        for (const r of numerics) {
          const p = (r.record as any).parameter as string
          if (!byParam[p]) byParam[p] = []
          byParam[p].push(r)
        }

        const result: LabSeries[] = []
        for (const [parameter, recs] of Object.entries(byParam)) {
          const ref = REFERENCE_RANGES[parameter]
          const sorted = recs.sort((a, b) =>
            (a.sort_date ?? "").localeCompare(b.sort_date ?? "")
          )
          result.push({
            parameter,
            unit: (recs[0].record as any).einheit ?? "",
            refLow: ref?.[0],
            refHigh: ref?.[1],
            data: sorted.map((r) => {
              const wert = (r.record as any).wert as number
              return {
                date: formatDate(r.sort_date),
                wert,
                flag: ref ? getFlag(wert, ref[0], ref[1]) : "normal",
              }
            }),
          })
        }

        // Nur Parameter mit ≥2 Messungen sind sinnvoll als Trend
        const filtered = result.filter((s) =>
          parameterFilter ? s.parameter === parameterFilter : s.data.length >= 2
        )
        setSeries(filtered.length > 0 ? filtered : null)
      })
      .catch(() => setSeries(null))
  }, [parameterFilter, reloadKey])

  const modal = modalOpen && (
    <AkteEntryModal
      entity="observations"
      title="Laborwerte"
      onClose={() => setModalOpen(false)}
      onSaved={() => setReloadKey((k) => k + 1)}
    />
  )

  const header = (
    <div className="flex items-center gap-3">
      <h2 className="text-base font-semibold text-zinc-100">Laborwerte</h2>
      <button
        onClick={() => setModalOpen(true)}
        className="ml-auto rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 px-3 py-1.5 text-sm font-medium hover:bg-rose-500/30 transition-colors whitespace-nowrap"
      >
        + Neu
      </button>
    </div>
  )

  if (series === null) {
    return (
      <div className="space-y-4">
        {header}
        <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
        {modal}
      </div>
    )
  }

  if (series.length === 0) {
    return (
      <div className="space-y-4">
        {header}
        <p className="text-sm text-zinc-500 text-center py-8">
          Keine Laborwerte mit Trends vorhanden (mindestens 2 Messungen nötig).
        </p>
        {modal}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {header}
      {series.map((s) => (
        <div key={s.parameter} className="space-y-2">
          <div className="flex items-center gap-3 text-sm">
            <span className="font-medium text-zinc-200">{s.parameter}</span>
            {s.refLow !== undefined && (
              <span className="text-xs text-zinc-600">
                Referenz: {s.refLow}–{s.refHigh === 999 ? "∞" : s.refHigh} {s.unit}
              </span>
            )}
          </div>
          <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4">
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={s.data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
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
                  width={40}
                />
                <Tooltip content={<CustomTooltip />} />
                {s.refHigh !== undefined && s.refHigh < 999 && (
                  <ReferenceLine
                    y={s.refHigh}
                    stroke="rgba(52,211,153,0.25)"
                    strokeDasharray="4 4"
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="wert"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#6366f1" }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
      {modal}
    </div>
  )
}