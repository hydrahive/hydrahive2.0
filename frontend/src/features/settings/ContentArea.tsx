import { Suspense, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ExternalLink, Loader2 } from "lucide-react"
import type { SettingsGroup } from "./registry"

interface Props {
  group: SettingsGroup
}

/**
 * Mittlerer Bereich: Karteikarten-Tabs oben + Inhalt darunter.
 *
 * Wenn group.component gesetzt ist, wird die bestehende Feature-Page direkt
 * eingebettet (in einem isolierten, scrollbaren Container — neutralisiert
 * etwaiges Vollbild-Layout der Page). Sonst: Platzhalter + Link zur alten Seite
 * (Gerüst-Phase, Inhalt folgt etappenweise).
 */
export function ContentArea({ group }: Props) {
  const [tab, setTab] = useState(group.tabs[0] ?? "")

  useEffect(() => { setTab(group.tabs[0] ?? "") }, [group.id, group.tabs])

  const Embedded = group.component

  return (
    <div className="flex h-full flex-col">
      {/* Karteikarten */}
      <div className="flex items-center gap-1 border-b border-white/8 px-4 pt-3">
        {group.tabs.map((tName) => (
          <button
            key={tName}
            onClick={() => setTab(tName)}
            className={`rounded-t-lg px-3.5 py-2 text-sm transition-colors ${
              tab === tName
                ? "bg-[#104E8B]/20 text-sky-200 border-b-2 border-sky-400"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[4%]"
            }`}
          >
            {tName}
          </button>
        ))}
      </div>

      {/* Inhalt */}
      <div className="flex-1 overflow-y-auto p-5">
        {Embedded ? (
          <Suspense fallback={
            <div className="flex h-40 items-center justify-center">
              <Loader2 size={20} className="animate-spin text-zinc-500" />
            </div>
          }>
            <Embedded />
          </Suspense>
        ) : (
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
        )}
      </div>
    </div>
  )
}
