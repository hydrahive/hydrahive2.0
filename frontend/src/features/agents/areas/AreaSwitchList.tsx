import { useTranslation } from "react-i18next"
import { AdminToggle } from "@/features/cockpit/admin/ui"
import { areaState } from "./areaItems"
import type { AreaCatalog } from "./areasApi"

interface Props {
  catalog: AreaCatalog
  items: Set<string>
  onToggle: (areaId: string, on: boolean) => void
  disabled?: boolean
}

/** Bereichs-Schalter (nur an/aus), nach Gruppen. Nie vergebbare Bereiche stehen ausgegraut mit Begründung da. */
export function AreaSwitchList({ catalog, items, onToggle, disabled }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-4">
      {catalog.groups.map((g) => {
        const areas = catalog.areas.filter((a) => a.group === g.id && a.tools.length > 0)
        if (areas.length === 0) return null
        return (
          <section key={g.id} aria-label={g.name}>
            <h4 className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[#9aa7bc]">{g.name}</h4>
            <ul className="space-y-1.5">
              {areas.map((a) => {
                const never = catalog.neverAreas.has(a.id)
                const state = never ? "off" : areaState(a, items, catalog.never)
                return (
                  <li key={a.id} className={`flex items-start gap-3 rounded-[4px] border border-s-rand bg-s-innen px-3 py-2 ${never ? "opacity-50" : ""}`}>
                    {/* teilweise = Häkchen aus, aber Hinweis: ein Klick schaltet den ganzen Bereich ein (Review #795) */}
                    <AdminToggle checked={state === "on"} disabled={disabled || never} data-state={state}
                      aria-label={a.name} onChange={() => onToggle(a.id, state !== "on")} />
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-[#e8eef8]">{a.name}</span>
                      <span className="block text-xs text-[#9aa7bc]">{never ? t("areas.never") : a.sentence}</span>
                      {state === "partial" && <span className="block text-[11px] text-amber-300" data-testid="pool-partial">{t("areas.pool_partial")}</span>}
                    </span>
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
