import { useEffect, useState } from "react"
import { fhirApi, type FhirTimelineEntry } from "../api"

const TYPE_COLORS: Record<string, string> = {
  Condition: "bg-red-500",
  MedicationRequest: "bg-blue-500",
  Observation: "bg-green-500",
  Encounter: "bg-purple-500",
  Immunization: "bg-yellow-500",
}

function entryTitle(entry: FhirTimelineEntry): string {
  const r = entry.resource
  if (entry.resource_type === "Condition") {
    const code = r.code as Record<string, unknown>
    const codings = (code?.coding as { display?: string }[]) ?? []
    return codings[0]?.display ?? (code?.text as string) ?? "Diagnose"
  }
  if (entry.resource_type === "Observation") {
    const code = r.code as Record<string, unknown>
    return (code?.text as string) ?? "Laborwert"
  }
  return entry.label
}

export function ZeitstrahlView() {
  const [entries, setEntries] = useState<FhirTimelineEntry[] | null>(null)

  useEffect(() => {
    fhirApi.getTimeline().then((d) => setEntries(d.entries)).catch(() => setEntries([]))
  }, [])

  if (entries === null) return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  if (entries.length === 0) return <p className="text-zinc-500 text-sm py-8 text-center">Noch keine Daten importiert.</p>

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">Zeitstrahl</h2>
      <div className="relative pl-6">
        <div className="absolute left-2 top-0 bottom-0 w-px bg-zinc-800" />
        {entries.map((entry, i) => (
          <div key={i} className="relative mb-4">
            <div className={`absolute -left-4 top-1.5 w-2 h-2 rounded-full ${TYPE_COLORS[entry.resource_type] ?? "bg-zinc-500"}`} />
            <div className="rounded-lg border border-white/[6%] bg-zinc-900/40 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-200">{entryTitle(entry)}</span>
                <span className="text-xs text-zinc-600">{entry.imported_at.slice(0, 10)}</span>
              </div>
              <span className="text-xs text-zinc-500">{entry.label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
