import { useEffect, useState } from "react"
import { fhirApi, type FhirSummary } from "../api"
import { FhirImportButton } from "../components/FhirImportButton"

const CATEGORIES = [
  { type: "Condition", icon: "🔴", label: "Diagnosen" },
  { type: "MedicationRequest", icon: "💊", label: "Medikamente" },
  { type: "Observation", icon: "🧪", label: "Laborwerte" },
  { type: "AllergyIntolerance", icon: "🤧", label: "Allergien" },
  { type: "Immunization", icon: "💉", label: "Impfungen" },
  { type: "Encounter", icon: "🏥", label: "Arztbesuche" },
]

export function UebersichtView() {
  const [summary, setSummary] = useState<FhirSummary | null>(null)

  const load = () => fhirApi.getSummary().then(setSummary).catch(() => setSummary({}))

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-100">Übersicht</h2>
        <FhirImportButton onImported={load} />
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
          <p className="text-zinc-500 text-sm">Noch keine Patientendaten importiert.</p>
          <p className="text-zinc-600 text-xs mt-1">Exportiere deine Akte aus der TK-App und lade die JSON-Datei hoch.</p>
        </div>
      )}
    </div>
  )
}
