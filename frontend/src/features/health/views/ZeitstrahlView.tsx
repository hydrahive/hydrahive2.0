import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { egaApi, type EgaTimelineEntry } from "../api"

const TYPE_COLORS: Record<string, string> = {
  Encounter:          "bg-purple-500",
  MedicationDispense: "bg-blue-500",
  Procedure:          "bg-green-500",
  Condition:          "bg-red-500",
  HospitalStay:       "bg-orange-500",
}

const TYPE_LABELS: Record<string, string> = {
  Encounter:          "Arztbesuch",
  MedicationDispense: "Medikament",
  Procedure:          "Vorsorge",
  Condition:          "Diagnose",
  HospitalStay:       "Krankenhaus",
}

export function ZeitstrahlView() {
  const { t } = useTranslation("health")
  const [entries, setEntries] = useState<EgaTimelineEntry[] | null>(null)

  useEffect(() => {
    egaApi.getTimeline().then((d) => setEntries(d.entries)).catch(() => setEntries([]))
  }, [])

  if (entries === null) return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  if (entries.length === 0) return <p className="text-zinc-500 text-sm py-8 text-center">{t("empty")}</p>

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">Zeitstrahl</h2>
      <div className="relative pl-6">
        <div className="absolute left-2 top-0 bottom-0 w-px bg-zinc-800" />
        {entries.map((entry) => (
          <div key={entry.id} className="relative mb-4">
            <div className={`absolute -left-4 top-1.5 w-2 h-2 rounded-full ${TYPE_COLORS[entry.dto_type] ?? "bg-zinc-500"}`} />
            <div className="rounded-lg border border-white/[6%] bg-zinc-900/40 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-200 truncate max-w-xs">{entry.display}</span>
                <span className="text-xs text-zinc-600 shrink-0 ml-2">{entry.sort_date ?? ""}</span>
              </div>
              <span className="text-xs text-zinc-500">{TYPE_LABELS[entry.dto_type] ?? entry.dto_type}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
