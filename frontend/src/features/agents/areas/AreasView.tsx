import { useTranslation } from "react-i18next"
import { AreaSwitch } from "./AreaSwitch"
import type { AreaCatalog, AreaStatus } from "./types"

interface Props {
  catalog: AreaCatalog
  status: AreaStatus
  mode: "classic" | "catalog"
  onMode: (m: "classic" | "catalog") => void
  onToggle: (areaId: string, on: boolean) => void
  onAdopt: (areaId: string) => void
}

/** Die Ansicht (ohne Laden/Speichern): Gruppen, Bereichs-Schalter, „Werkzeuge bei Bedarf suchen“. Für Nicht-Admins nur lesbar. */
export function AreasView({ catalog, status, mode, onMode, onToggle, onAdopt }: Props) {
  const { t } = useTranslation("agents")
  const locked = !status.editable
  const states = new Map(status.areas.map((s) => [s.id, s]))
  return (
    <div className="space-y-4" data-testid="areas-view">
      {locked && <p className="text-[11px] text-amber-400/90" role="note">{t("areas.readonly")}</p>}
      <div className="rounded-md border border-white/[8%] bg-white/[2%] px-3 py-2.5 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-zinc-200">{t("areas.catalog_mode")}</p>
          <p className="text-[10px] text-zinc-500">{t("areas.catalog_mode_hint")}</p>
        </div>
        <button
          type="button" role="switch" data-testid="catalog-mode-switch" aria-checked={mode === "catalog"} disabled={locked}
          aria-label={t("areas.catalog_mode")} onClick={() => onMode(mode === "catalog" ? "classic" : "catalog")}
          className={`relative w-9 h-5 rounded-full shrink-0 transition-colors disabled:opacity-50 ${mode === "catalog" ? "bg-violet-600" : "bg-white/10"}`}
        >
          <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${mode === "catalog" ? "translate-x-4" : ""}`} />
        </button>
      </div>
      {catalog.groups.map((g) => {
        const rows = catalog.areas.filter((a) => a.group === g.id && states.has(a.id))
        if (rows.length === 0) return null
        return (
          <section key={g.id} className="space-y-1">
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400 px-1">{g.name}</h3>
            <div className="rounded-md border border-white/[8%] bg-white/[2%] divide-y divide-white/[5%]">
              {rows.map((a) => {
                const s = states.get(a.id)!
                return (
                  <AreaSwitch
                    key={a.id} area={a} state={s} disabled={locked}
                    onToggle={() => onToggle(a.id, s.state !== "on")} onAdoptNew={() => onAdopt(a.id)}
                  />
                )
              })}
            </div>
          </section>
        )
      })}
    </div>
  )
}
