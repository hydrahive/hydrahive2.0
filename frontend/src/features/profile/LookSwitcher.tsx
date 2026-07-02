import type { CSSProperties } from "react"
import { Check, Layers } from "lucide-react"
import { useState } from "react"
import { rgbFor } from "@/shared/colors"
import { applyLook, getStoredLook, LOOKS, type LookId } from "@/shared/look"

export function LookSwitcher() {
  const [active, setActive] = useState<LookId>(getStoredLook())

  function pick(id: LookId) {
    applyLook(id)
    setActive(id)
  }

  return (
    <div className="box overflow-hidden p-5 space-y-3" style={{ "--c": rgbFor("/profile") } as CSSProperties}>
      <div>
        <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
          <Layers size={14} className="text-[var(--hh-accent-text)]" />
          Oberflächen-Stil
        </h2>
        <p className="text-xs text-zinc-500 mt-0.5">
          Verändert Form, Ränder und Dichte der Oberfläche — unabhängig von der Farbe.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {LOOKS.map((lk) => {
          const isActive = lk.id === active
          return (
            <button
              key={lk.id}
              onClick={() => pick(lk.id)}
              className={`flex items-start gap-3 px-3 py-2.5 rounded-lg border transition-all text-left ${
                isActive
                  ? "border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)]"
                  : "border-white/[8%] hover:border-white/20 hover:bg-white/[3%]"
              }`}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-100 truncate flex items-center gap-1.5">
                  {lk.name}
                  {isActive && <Check size={12} className="text-[var(--hh-accent-text)]" />}
                </p>
                <p className="text-[11px] text-zinc-500">{lk.description}</p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
