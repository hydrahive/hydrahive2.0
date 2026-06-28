import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ExternalLink } from "lucide-react"
import type { SettingsGroup } from "./registry"

interface Props {
  group: SettingsGroup
}

/**
 * Mittlerer Bereich: Karteikarten-Tabs oben + Inhalt darunter.
 * Gerüst-Phase: der eigentliche Inhalt wird etappenweise migriert. Bis dahin
 * zeigt jeder Tab einen Platzhalter + (falls vorhanden) einen Link zur
 * bestehenden Seite, damit nichts unerreichbar ist.
 */
export function ContentArea({ group }: Props) {
  const [tab, setTab] = useState(group.tabs[0] ?? "")

  // Beim Gruppenwechsel auf den ersten Tab zurück.
  useEffect(() => { setTab(group.tabs[0] ?? "") }, [group.id, group.tabs])

  return (
    <div className="flex h-full flex-col">
      {/* Karteikarten */}
      <div className="flex items-center gap-1 border-b border-white/8 px-4 pt-3">
        {group.tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-t-lg px-3.5 py-2 text-sm transition-colors ${
              tab === t
                ? "bg-[#104E8B]/20 text-sky-200 border-b-2 border-sky-400"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[4%]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Inhalt */}
      <div className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-xl border border-white/8 bg-zinc-900/40 p-6">
            <h3 className="text-base font-semibold text-zinc-100">{group.label} · {tab}</h3>
            <p className="mt-2 text-sm text-zinc-400">
              Dieser Bereich wird hierher umgezogen. Die Struktur steht — der
              Inhalt folgt Schritt für Schritt.
            </p>
            {group.route && (
              <Link
                to={group.route}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#104E8B]/30 px-3.5 py-2 text-sm text-sky-200 ring-1 ring-inset ring-[#104E8B]/50 hover:bg-[#104E8B]/40 transition-colors"
              >
                <ExternalLink size={14} />
                Aktuelle Seite öffnen
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
