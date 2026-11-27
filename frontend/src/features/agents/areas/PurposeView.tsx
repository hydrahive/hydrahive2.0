import { useTranslation } from "react-i18next"
import type { Area, AreaCatalog, Suggestion } from "./types"

export const MAX_PURPOSE = 500
const MAX_REASON = 200

export interface Resolved { area: Area; reason: string }

/**
 * Löst Vorschläge gegen den Katalog auf (Review #791 Sicherheit): Name und Satz kommen NUR aus dem Katalog, nie vom Modell;
 * unbekannte IDs, Dubletten und kaputte Einträge fallen still weg; der Grund wird auf Text gekürzt (Nicht-Text → leer).
 */
export function resolveSuggestions(raw: Suggestion[], catalog: AreaCatalog): Resolved[] {
  if (!Array.isArray(raw)) return []
  const byId = new Map(catalog.areas.map((a) => [a.id, a]))
  const seen = new Set<string>()
  const out: Resolved[] = []
  for (const s of raw) {
    if (!s || typeof s !== "object" || typeof s.area !== "string") continue
    const area = byId.get(s.area)
    if (!area || seen.has(area.id)) continue
    seen.add(area.id)
    out.push({ area, reason: typeof s.reason === "string" ? s.reason.slice(0, MAX_REASON) : "" })
  }
  return out
}

interface ViewProps {
  purpose: string
  onPurpose: (v: string) => void
  onSuggest: () => void
  busy: boolean
  suggestions: Resolved[]
  picked: string[]
  onToggle: (areaId: string) => void
  onApply: () => void
  error: string | null
}

/** Ansicht des Zweck-Vorschlags: Feld, Knopf, Liste mit Häkchen. Der Grund wird nur als Text gerendert (kein HTML). */
export function PurposeView({ purpose, onPurpose, onSuggest, busy, suggestions, picked, onToggle, onApply, error }: ViewProps) {
  const { t } = useTranslation("agents")
  return (
    <div className="rounded-md border border-white/[8%] bg-white/[2%] px-3 py-2.5 space-y-2" data-testid="purpose-suggest">
      <label className="block text-xs font-medium text-zinc-200">{t("areas.purpose_label")}</label>
      <div className="flex gap-2">
        <input
          value={purpose} maxLength={MAX_PURPOSE} placeholder={t("areas.purpose_placeholder")} onChange={(e) => onPurpose(e.target.value)}
          className="flex-1 rounded-md border border-white/[8%] bg-white/[3%] px-2 py-1 text-xs text-zinc-200"
        />
        <button
          type="button" data-testid="suggest-button" disabled={busy || !purpose.trim()} onClick={onSuggest}
          className="px-3 py-1 rounded-md bg-violet-600 text-xs text-white disabled:opacity-40"
        >
          {busy ? t("areas.purpose_busy") : t("areas.purpose_button")}
        </button>
      </div>
      {error && <p className="text-[11px] text-rose-300" role="alert">{error}</p>}
      {suggestions.length > 0 && (
        <div className="space-y-1.5">
          <ul className="space-y-1">
            {suggestions.map(({ area, reason }) => (
              <li key={area.id} className="flex items-start gap-2 text-[11px]">
                <input type="checkbox" checked={picked.includes(area.id)} onChange={() => onToggle(area.id)} aria-label={area.name} className="mt-0.5" />
                <span><span className="text-zinc-200">{area.name}</span>{reason && <span className="text-zinc-500"> – {reason}</span>}</span>
              </li>
            ))}
          </ul>
          <button
            type="button" data-testid="apply-button" disabled={picked.length === 0} onClick={onApply}
            className="px-3 py-1 rounded-md bg-violet-600 text-xs text-white disabled:opacity-40"
          >
            {t("areas.purpose_apply")}
          </button>
          <p className="text-[10px] text-zinc-500">{t("areas.purpose_hint")}</p>
        </div>
      )}
    </div>
  )
}
