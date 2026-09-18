import { Suspense, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ExternalLink, Loader2 } from "lucide-react"
import type { SettingsGroup } from "./registry"
import { EmbedFrame } from "./EmbedFrame"

interface Props {
  group: SettingsGroup
  subItem?: string | null
}

/**
 * Mittlerer Bereich: Karteikarten-Tabs oben + Inhalt darunter.
 *
 * Render-Priorität:
 *  1. detailComponent (Gruppe mit Submenü) → bekommt die gewählte itemId.
 *  2. tabComponents[tab] → Per-Tab-Inhalt.
 *  3. component (+ fullscreen → EmbedFrame) → ganze Feature-Page.
 *  4. Platzhalter + Link (noch nicht migriert).
 */
export function ContentArea({ group, subItem = null }: Props) {
  const [tab, setTab] = useState(group.tabs[0] ?? "")

  useEffect(() => { setTab(group.tabs[0] ?? "") }, [group.id, group.tabs])

  const Detail = group.detailComponent
  // Per-Tab-Komponente hat Vorrang, sonst die gruppenweite component.
  const tabComp = group.tabComponents?.[tab]
  const Embedded = tabComp ?? group.component
  // EmbedFrame nur für gruppenweite Vollbild-Pages (nicht für Tab-Overrides).
  const useFrame = !tabComp && Boolean(group.fullscreen)

  // Detail-Komponente (Submenü-Schema) bringt ihr eigenes vollständiges Layout
  // (Header + eigene Karteikarten-Reiter + Save-Bar) — daher ohne äußere Tabs
  // und ohne Padding, volle Höhe.
  if (Detail) {
    return (
      <div className="h-full">
        <Suspense fallback={
          <div className="flex h-full items-center justify-center">
            <Loader2 size={20} className="animate-spin text-zinc-500" />
          </div>
        }>
          <Detail itemId={subItem} />
        </Suspense>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Karteikarten */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-[#2a364b] px-3 pt-3">
        {group.tabs.map((tName) => (
          <button
            key={tName}
            onClick={() => setTab(tName)}
            className={`shrink-0 rounded-[4px] border px-3 py-2 text-sm transition-colors ${
              tab === tName
                ? "border-[#69d7ff]/40 bg-[#1c2940] font-semibold text-[#69d7ff]"
                : "border-transparent text-[#8d9ab0] hover:border-[#2a364b] hover:bg-[#151c2b] hover:text-[#e8eef8]"
            }`}
          >
            {tName}
          </button>
        ))}
      </div>

      {/* Inhalt */}
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {Embedded && useFrame ? (
          <EmbedFrame><Embedded /></EmbedFrame>
        ) : Embedded ? (
          <Suspense fallback={
            <div className="flex h-40 items-center justify-center">
              <Loader2 size={20} className="animate-spin text-zinc-500" />
            </div>
          }>
            <Embedded />
          </Suspense>
        ) : (
          <div className="mx-auto max-w-3xl">
            <div className="rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-4">
              <h3 className="text-base font-bold text-[#e8eef8]">{group.label} · {tab}</h3>
              <p className="mt-2 text-sm text-[#8d9ab0]">
                Dieser Bereich wird hierher umgezogen. Die Struktur steht — der
                Inhalt folgt Schritt für Schritt.
              </p>
              {group.route && (
                <Link
                  to={group.route}
                  className="mt-4 inline-flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/40 bg-[#163248] px-3 py-2 text-sm font-semibold text-[#c8f2ff] transition-colors hover:bg-[#1b3d56]"
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
