import type { CSSProperties } from "react"
import { Check, LayoutTemplate } from "lucide-react"
import { useState } from "react"
import { rgbFor } from "@/shared/colors"
import { getStoredThemeId, storeThemeId, THEMES } from "@/shared/themes/registry"

/** Theme-Picker: wählt das aktive Layout-Theme (Menü oben / Sidebar / …).
 *  Speichert in localStorage und benachrichtigt den LayoutHost live. */
export function ThemePicker() {
  const [active, setActive] = useState<string>(getStoredThemeId())

  function pick(id: string) {
    storeThemeId(id)
    setActive(id)
    window.dispatchEvent(new Event("hh-theme-change"))
  }

  return (
    <div className="box overflow-hidden p-5 space-y-3" style={{ "--c": rgbFor("/profile") } as CSSProperties}>
      <div>
        <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
          <LayoutTemplate size={14} className="text-[var(--hh-accent-text)]" />
          Design
        </h2>
        <p className="text-xs text-zinc-500 mt-0.5">
          Wechselt das komplette Layout der Oberfläche — nicht nur die Farbe.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {THEMES.map((th) => {
          const isActive = th.id === active
          return (
            <button
              key={th.id}
              onClick={() => pick(th.id)}
              className={`flex items-start gap-3 px-3 py-2.5 rounded-lg border transition-all text-left ${
                isActive
                  ? "border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)]"
                  : "border-white/[8%] hover:border-white/20 hover:bg-white/[3%]"
              }`}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-100 flex items-center gap-1.5">
                  {th.name}
                  {isActive && <Check size={12} className="text-[var(--hh-accent-text)]" />}
                </p>
                <p className="text-[11px] text-zinc-500">{th.description}</p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
