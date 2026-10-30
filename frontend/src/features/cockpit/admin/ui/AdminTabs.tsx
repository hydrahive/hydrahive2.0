import { useRef, type KeyboardEvent, type ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { nextTab } from "./adminTabs"

export interface AdminTab<T extends string = string> {
  id: T
  label: string
  /** Anzahl hinter dem Namen (z. B. Einträge). */
  count?: number
  /** Punkt: in diesem Reiter ist etwas (läuft, Fehler, ungespeichert). */
  dot?: boolean
}

interface Props<T extends string> {
  /** Name der Reiterleiste für Bildschirmleser. */
  label: string
  /** Eindeutiger Präfix für die IDs (mehrere Reiterleisten auf einer Seite). */
  idPrefix: string
  tabs: readonly AdminTab<T>[]
  active: T
  onSelect: (id: T) => void
  /** Viele Reiter (z. B. 10 Einstellungs-Gruppen): festes Raster mit gleich breiten Reitern statt einer Zeile. */
  grid?: boolean
  children: ReactNode
}

/**
 * Reiter für Admin-Fenster (Plan admin-reiter-archiv, Regel „Seiten kurz halten“). Der Aufrufer hält den
 * aktiven Reiter in der Adresse (`tab=`, siehe adminTabs.ts). Tastatur: ←/→ wechseln, nur der aktive Reiter
 * ist per Tab erreichbar (WAI-ARIA Tabs).
 */
export function AdminTabs<T extends string>({ label, idPrefix, tabs, active, onSelect, grid, children }: Props<T>) {
  const { t } = useTranslation("common")
  const leiste = useRef<HTMLDivElement>(null)
  const ids = tabs.map((tab) => tab.id)

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return
    event.preventDefault()
    const ziel = nextTab(ids, active, event.key === "ArrowRight" ? 1 : -1)
    onSelect(ziel)
    leiste.current?.querySelector<HTMLButtonElement>(`#${idPrefix}-tab-${ziel}`)?.focus()
  }

  return (
    <div className="space-y-3">
      <div ref={leiste} role="tablist" aria-label={label} onKeyDown={onKeyDown}
        className={`grid grid-cols-2 gap-1 rounded-[4px] border border-s-rand bg-s-innen p-1 ${
          grid ? "sm:grid-cols-3 lg:grid-cols-4" : "sm:flex sm:flex-wrap"}`}>
        {tabs.map((tab) => {
          const an = tab.id === active
          return (
            <button key={tab.id} type="button" role="tab" id={`${idPrefix}-tab-${tab.id}`}
              aria-selected={an} aria-controls={`${idPrefix}-pane`} tabIndex={an ? 0 : -1}
              onClick={() => onSelect(tab.id)}
              className={`relative flex min-w-0 items-center justify-center gap-1.5 rounded-[3px] py-2 text-xs font-bold transition-colors sm:flex-auto sm:text-sm ${grid ? "px-2" : "px-3"} ${
                an ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#9aa7bc] hover:bg-s-hebung hover:text-[#e8eef8]"
              }`}>
              <span className="truncate">{tab.label}</span>
              {tab.count !== undefined && (
                <span className="rounded-full bg-s-tief px-1.5 text-[10px] font-bold text-[#9aa7bc]">{tab.count}</span>
              )}
              {tab.dot && (
                <span data-tab-dot={tab.id} className="h-2 w-2 shrink-0 rounded-full bg-amber-300">
                  <span className="sr-only">{t("tabs.attention")}</span>
                </span>
              )}
            </button>
          )
        })}
      </div>
      <div id={`${idPrefix}-pane`} role="tabpanel" aria-labelledby={`${idPrefix}-tab-${active}`}>
        {children}
      </div>
    </div>
  )
}
