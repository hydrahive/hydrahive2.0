import { useEffect, useState } from "react"
import { egaApi } from "../api"
import { EgaImportButton } from "../components/EgaImportButton"

const CATEGORIES = [
  { type: "Encounter",           icon: "🏥", label: "Arztbesuche" },
  { type: "AmbulantClaim",       icon: "🧾", label: "Abrechnungen" },
  { type: "MedicationDispense",  icon: "💊", label: "Medikamente" },
  { type: "HospitalStay",        icon: "🛏", label: "Krankenhaus" },
  { type: "Procedure",           icon: "🔬", label: "Vorsorge" },
  { type: "Condition",           icon: "📋", label: "Diagnosen" },
]

export function UebersichtView() {
  const [summary, setSummary] = useState<Record<string, number> | null>(null)

  const load = () => egaApi.getSummary().then(setSummary).catch(() => setSummary({}))

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-100">Übersicht</h2>
        <EgaImportButton onImported={load} />
      </div>

      {summary === null ? (
        <div className="grid grid-cols-3 gap-3">
          {CATEGORIES.map((c) => (
            <div key={c.type} className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {CATEGORIES.map((c) => (
            <div key={c.type} className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4">
              <div className="text-lg mb-1">{c.icon}</div>
              <div className="text-2xl font-bold text-zinc-100">{summary[c.type] ?? 0}</div>
              <div className="text-xs text-zinc-500 mt-0.5">{c.label}</div>
            </div>
          ))}
        </div>
      )}

      {summary && Object.keys(summary).length === 0 && (
        <div className="rounded-xl border border-dashed border-white/10 p-8 text-center">
          <p className="text-zinc-500 text-sm">Noch keine Gesundheitsdaten importiert.</p>
          <p className="text-zinc-600 text-xs mt-1">TK-Safe App öffnen → Akte exportieren → ZIP hier hochladen.</p>
        </div>
      )}
    </div>
  )
}
