import { useTranslation } from "react-i18next"
import { neverGiven } from "./helperPool"
import type { Area } from "./types"

interface ViewProps {
  areas: Area[]
  forbidden: string[]
  enabled: boolean
  selected: string[]
  mayEdit: boolean
  busy: boolean
  dirty: boolean
  onToggleEnabled: () => void
  onToggleArea: (areaId: string) => void
  onSave: () => void
  error?: string | null
  done?: boolean
}

const box = "rounded-md border border-white/[8%] bg-white/[2%] px-3 py-2.5 space-y-2"

/** Die Ansicht des Helfer-Bereichs (ohne Laden/Speichern): Schalter, darunter Bereiche an/aus, Nicht-Vergebbares ausgegraut. */
export function HelperView({ areas, forbidden, enabled, selected, mayEdit, busy, dirty, onToggleEnabled, onToggleArea, onSave, error, done }: ViewProps) {
  const { t } = useTranslation("agents")
  return (
    <div className={box} data-testid="helper-switch">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-zinc-200">{t("areas.helper_title")}</p>
          <p className="text-[10px] text-zinc-500">{mayEdit ? t("areas.helper_hint") : t("areas.helper_readonly")}</p>
        </div>
        <button
          type="button" role="switch" aria-checked={enabled} aria-label={t("areas.helper_title")} disabled={!mayEdit} onClick={onToggleEnabled}
          className={`relative w-9 h-5 rounded-full shrink-0 transition-colors disabled:opacity-50 ${enabled ? "bg-violet-600" : "bg-white/10"}`}
        >
          <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${enabled ? "translate-x-4" : ""}`} />
        </button>
      </div>
      {enabled && (
        <div className="divide-y divide-white/[5%]">
          {areas.map((a) => {
            const never = neverGiven(a, forbidden)
            const on = selected.includes(a.id)
            return (
              <div key={a.id} data-area={a.id} aria-disabled={never} className={`flex items-center justify-between gap-3 py-1.5 ${never ? "opacity-40" : ""}`}>
                <div className="min-w-0">
                  <p className="text-[11px] text-zinc-300">{a.name}</p>
                  {never && <p className="text-[10px] text-zinc-500">{t("areas.helper_never")}</p>}
                </div>
                <button
                  type="button" role="switch" aria-checked={on} aria-label={a.name} disabled={!mayEdit || never} onClick={() => onToggleArea(a.id)}
                  className={`relative w-7 h-4 rounded-full shrink-0 disabled:opacity-50 ${on ? "bg-violet-600" : "bg-white/10"}`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white transition-transform ${on ? "translate-x-3" : ""}`} />
                </button>
              </div>
            )
          })}
        </div>
      )}
      {error && <p className="text-[11px] text-red-400" role="alert">{error}</p>}
      {done && <p className="text-[11px] text-emerald-400">{t("areas.helper_saved")}</p>}
      {mayEdit && (
        <button type="button" disabled={!dirty || busy} onClick={onSave} className="px-3 py-1 rounded-md bg-violet-600 text-xs text-white disabled:opacity-40">
          {t("areas.helper_save")}
        </button>
      )}
    </div>
  )
}
