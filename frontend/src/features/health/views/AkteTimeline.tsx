import { useEffect, useState } from "react"
import { akteApi, type AkteEntityKey, type AkteTimelineEntry } from "../api"
import { VerifyBadge } from "../components/VerifyBadge"

const ENTITY_ICONS: Record<string, string> = {
  conditions:    "🔴",
  medications:   "💊",
  observations:  "🧪",
  events:        "📋",
  imaging:       "🩻",
  allergies:     "⚠️",
  practitioners: "👨‍⚕️",
  documents:     "📄",
  notes:         "📝",
}

const ENTITY_LABELS: Record<string, string> = {
  conditions:    "Diagnose",
  medications:   "Medikament",
  observations: "Laborwert",
  events:        "Ereignis",
  imaging:       "Bildgebung",
  allergies:     "Allergie",
  practitioners: "Arzt",
  documents:     "Dokument",
  notes:         "Notiz",
}

type FilterEntity = AkteEntityKey | "all"

export function AkteTimeline() {
  const [entries, setEntries] = useState<AkteTimelineEntry[] | null>(null)
  const [filter, setFilter] = useState<FilterEntity>("all")
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    akteApi.getTimeline()
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleVerify = async (entity: AkteEntityKey, eid: string) => {
    await akteApi.verifyEntity(entity, eid)
    setEntries((prev) =>
      prev?.map((e) => eid === e.record?.id || e.record?.id === eid
        ? { ...e, verifiziert: 1 }
        : e
      )
    )
  }

  if (loading) {
    return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  const filtered = filter === "all"
    ? entries
    : entries?.filter((e) => e.entity === filter)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilter("all")}
          className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
            filter === "all"
              ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
              : "text-zinc-500 border-white/[6%] hover:bg-white/[4%]"
          }`}
        >
          Alle
        </button>
        {(Object.keys(ENTITY_ICONS) as AkteEntityKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors border flex items-center gap-1.5 ${
              filter === key
                ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                : "text-zinc-500 border-white/[6%] hover:bg-white/[4%]"
            }`}
          >
            <span>{ENTITY_ICONS[key]}</span>
            <span>{ENTITY_LABELS[key]}</span>
          </button>
        ))}
      </div>

      {(!filtered || filtered.length === 0) && (
        <p className="text-sm text-zinc-500 py-8 text-center">
          {entries === null ? "Laden…" : "Noch keine Einträge vorhanden."}
        </p>
      )}

      {filtered && filtered.length > 0 && (
        <div className="relative pl-6">
          <div className="absolute left-2 top-0 bottom-0 w-px bg-zinc-800" />
          {filtered.map((entry) => (
            <div key={entry.record?.id as string ?? entry.sort_date + entry.entity} className="relative mb-4">
              <div
                className={`absolute -left-4 top-1.5 w-2 h-2 rounded-full ${
                  entry.verifiziert ? "bg-emerald-400" : "bg-orange-400"
                }`}
              />
              <div className="rounded-lg border border-white/[6%] bg-zinc-900/40 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <VerifyBadge verifiziert={entry.verifiziert} onVerify={() => {
                      if (!entry.verifiziert) {
                        handleVerify(entry.entity, entry.record?.id as string)
                      }
                    }} />
                    <span className="text-sm text-zinc-200 truncate">{entry.label}</span>
                  </div>
                  <span className="text-xs text-zinc-600 shrink-0">
                    {entry.sort_date ? new Date(entry.sort_date).toLocaleDateString("de-DE") : ""}
                  </span>
                </div>
                <span className="text-xs text-zinc-500">{ENTITY_ICONS[entry.entity]} {ENTITY_LABELS[entry.entity]}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}