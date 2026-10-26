import { Suspense, useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import type { SettingsGroup } from "./registry"
import { CONTENT_WIDTH } from "./layout"

/**
 * Inhalt eines Reiters von „Meine Einstellungen“.
 * Innere Reiter nur, wenn die Gruppe mehrere Teile hat (z. B. Kommunikation: Discord · WhatsApp · Mail).
 * `fullHeight`-Inhalte (Butler-Editor, Agenten/Projekte) bekommen die volle Höhe ohne Innenabstand.
 * Alles sitzt mittig in derselben Höchstbreite wie der Kopf (CONTENT_WIDTH); nur `wide` (Butler) nutzt die volle Breite.
 */

export function ContentArea({ group }: { group: SettingsGroup }) {
  const [tab, setTab] = useState(group.tabs[0] ?? "")
  useEffect(() => { setTab(group.tabs[0] ?? "") }, [group.id, group.tabs])

  const Content = group.tabComponents?.[tab] ?? group.component
  const loading = (
    <div className="flex h-40 items-center justify-center">
      <Loader2 size={20} className="animate-spin text-zinc-500" />
    </div>
  )

  return (
    <div className={`flex h-full min-h-0 flex-col ${group.wide ? "" : CONTENT_WIDTH}`}>
      {group.tabs.length > 1 && (
        <div role="tablist" aria-label={group.label} className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-[#2a364b] px-3 py-1.5">
          {group.tabs.map((name) => (
            <button key={name} type="button" role="tab" aria-selected={tab === name} onClick={() => setTab(name)}
              className={`shrink-0 rounded-[3px] px-3 py-1 text-xs font-semibold transition-colors ${
                tab === name ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#8d9ab0] hover:bg-white/5 hover:text-[#e8eef8]"
              }`}>{name}</button>
          ))}
        </div>
      )}
      <div className={group.fullHeight ? "min-h-0 flex-1 overflow-hidden" : "min-h-0 flex-1 overflow-y-auto p-4"}>
        {Content && <Suspense fallback={loading}><Content /></Suspense>}
      </div>
    </div>
  )
}
