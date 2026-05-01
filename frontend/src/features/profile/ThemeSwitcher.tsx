import { Check, Palette } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { applyTheme, getStoredTheme, THEMES, type ThemeId } from "@/shared/theme"

export function ThemeSwitcher() {
  const { t } = useTranslation("profile")
  const [active, setActive] = useState<ThemeId>(getStoredTheme())

  function pick(id: ThemeId) {
    applyTheme(id)
    setActive(id)
  }

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
          <Palette size={14} className="text-[var(--hh-accent-text)]" />
          {t("theme.title")}
        </h2>
        <p className="text-xs text-zinc-500 mt-0.5">{t("theme.description")}</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {THEMES.map((th) => {
          const isActive = th.id === active
          return (
            <button
              key={th.id}
              onClick={() => pick(th.id)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all text-left ${
                isActive
                  ? "border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)]"
                  : "border-white/[8%] hover:border-white/20 hover:bg-white/[3%]"
              }`}
            >
              <div
                className="w-9 h-9 rounded-md flex-shrink-0 shadow-md"
                style={{ background: `linear-gradient(135deg, ${th.preview.from}, ${th.preview.to})` }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-100 truncate flex items-center gap-1.5">
                  {th.name}
                  {isActive && <Check size={12} className="text-[var(--hh-accent-text)]" />}
                </p>
                <p className="text-[11px] text-zinc-500 truncate">{th.description}</p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
