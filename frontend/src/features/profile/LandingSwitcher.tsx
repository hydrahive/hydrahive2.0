import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { useUserPreferences } from "@/features/preferences/useUserPreferences"
import { LANDINGS, type Landing } from "./landing"

/** Startseite nach dem Anmelden – am Server gespeichert, gilt auf allen Geräten (docs/specs/startdesktop.md). */
export function LandingSwitcher() {
  const { t } = useTranslation("profile")
  const prefs = useUserPreferences()
  const current = prefs.preferences.landing

  function pick(v: Landing) {
    void prefs.patch({ landing: v }).catch(() => { /* Anzeige bleibt beim alten Wert */ })
  }

  return (
    <div className="box overflow-hidden p-5 space-y-3" style={{ "--c": rgbFor("/profile") } as CSSProperties}>
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">{t("landing.title")}</h2>
        <p className="text-xs text-zinc-500 mt-0.5">{t("landing.description")}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {LANDINGS.map((value) => (
          <button
            key={value}
            type="button"
            disabled={prefs.loading}
            onClick={() => pick(value)}
            aria-pressed={current === value}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border disabled:opacity-50 ${
              current === value
                ? "bg-violet-600/20 border-violet-500/50 text-violet-300"
                : "bg-white/[3%] border-white/[8%] text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {t(`landing.${value}`)}
          </button>
        ))}
      </div>
    </div>
  )
}
