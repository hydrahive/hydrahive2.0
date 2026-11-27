import { useTranslation } from "react-i18next"
import type { Area, AreaState, Mark } from "./types"

const GLYPH: Record<Mark, string> = { risky: "⚠️", private: "🔒", costly: "💶" }

interface Props {
  area: Area
  state: AreaState
  disabled: boolean
  onToggle: () => void
  onAdoptNew: () => void
}

/** Ein Bereichs-Schalter: Name, Satz, Zeichen mit Erklärung, Zustand an/aus/teilweise (ein Klick auf „teilweise“ schaltet ein). */
export function AreaSwitch({ area, state, disabled, onToggle, onAdoptNew }: Props) {
  const { t } = useTranslation("agents")
  const on = state.state === "on"
  const partial = state.state === "partial"
  const knob = on ? "translate-x-4" : partial ? "translate-x-2" : "translate-x-0"
  return (
    <div className="px-3 py-2 space-y-1" data-area={area.id}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-zinc-200">
            {area.name}
            {area.marks.map((m) => (
              <span key={m} title={t(`areas.mark_${m}`)} className="ml-1.5 text-[11px]">{GLYPH[m]}</span>
            ))}
          </p>
          <p className="text-[10px] text-zinc-500">{area.sentence}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={partial ? "mixed" : on}
          aria-label={area.name}
          data-state={state.state}
          disabled={disabled}
          onClick={onToggle}
          className={`relative w-9 h-5 rounded-full shrink-0 transition-colors disabled:opacity-50 ${
            on ? "bg-violet-600" : partial ? "bg-violet-600/50" : "bg-white/10"
          }`}
        >
          <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${knob}`} />
        </button>
      </div>
      {partial && <p className="text-[10px] text-amber-400/80">{t("areas.partial_hint")}</p>}
      {state.via_category.length > 0 && <p className="text-[10px] text-zinc-500">{t("areas.via_category")}</p>}
      {state.new.length > 0 && (
        <p className="text-[10px] text-sky-300" data-testid="adopt-new">
          {t("areas.new_tools", { count: state.new.length })}{" "}
          <button type="button" disabled={disabled} onClick={onAdoptNew} className="underline disabled:opacity-50">
            {t("areas.adopt")}
          </button>
        </p>
      )}
    </div>
  )
}
