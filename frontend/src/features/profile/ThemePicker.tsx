import type { CSSProperties } from "react"
import { Check, LayoutTemplate, Package } from "lucide-react"
import { useState } from "react"
import { rgbFor } from "@/shared/colors"
import { getStoredThemeId, storeThemeId, THEMES } from "@/shared/themes/registry"

/** Theme-Picker: wählt das aktive Layout-Theme (Menü oben / Sidebar / eigene
 *  Pakete). Speichert in localStorage und benachrichtigt den LayoutHost live. */
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
          Eigene Designs landen als Paket im Ordner <code className="text-zinc-400">src/themes/</code>.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {THEMES.map((th) => {
          const isActive = th.id === active
          return (
            <button
              key={th.id}
              onClick={() => pick(th.id)}
              className={`flex flex-col gap-2 px-3 py-2.5 rounded-lg border transition-all text-left ${
                isActive
                  ? "border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)]"
                  : "border-white/[8%] hover:border-white/20 hover:bg-white/[3%]"
              }`}
            >
              {th.preview && (
                <img
                  src={th.preview}
                  alt=""
                  className="w-full h-20 object-cover rounded-md border border-white/[6%]"
                />
              )}
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-100 flex items-center gap-1.5">
                    {th.name}
                    {isActive && <Check size={12} className="text-[var(--hh-accent-text)]" />}
                  </p>
                  <p className="text-[11px] text-zinc-500">{th.description}</p>
                </div>
                {th.source === "user" && (
                  <span
                    className="flex items-center gap-1 text-[10px] text-zinc-400 bg-white/[5%] px-1.5 py-0.5 rounded shrink-0"
                    title={th.author ? `von ${th.author}` : "Eigenes Theme-Paket"}
                  >
                    <Package size={9} /> Eigenes
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
