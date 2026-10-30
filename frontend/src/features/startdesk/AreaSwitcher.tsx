// Bereichs-Umschalter ▾ in der Bereichs-Leiste (docs/specs/startdesktop.md).
import { useEffect, useState } from "react"
import { ChevronDown } from "lucide-react"
import type { FilledArea } from "./areaLogic"

interface Props {
  areas: FilledArea[]
  active: FilledArea | null
  onPick: (area: FilledArea) => void
}

export function AreaSwitcher({ areas, active, onPick }: Props) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false) }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])
  const Icon = active?.area.icon

  return (
    <div className="relative min-w-0 shrink-0">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="menu"
        className={`flex max-w-[52vw] items-center gap-1.5 rounded-[4px] border border-s-rand bg-s-tief px-2.5 py-1.5 text-sm font-bold hover:border-s-rand-hover sm:max-w-none ${active?.area.text ?? "text-[#69d7ff]"}`}>
        {Icon && <Icon size={15} className="shrink-0" />}
        <span className="truncate">{active ? active.area.title : "Bereich wählen"}</span>
        <ChevronDown size={14} className="shrink-0 text-[#9aa7bc]" />
      </button>
      {open && <>
        <button type="button" className="fixed inset-0 z-[119] cursor-default" aria-label="Bereiche schließen" onClick={() => setOpen(false)} />
        <div role="menu" aria-label="Bereiche" className="absolute left-0 top-10 z-[120] w-[min(300px,calc(100vw-24px))] rounded-[6px] border border-s-rand bg-s-box p-1 shadow-2xl">
          {areas.map((a) => {
            const AIcon = a.area.icon
            const on = a.area.id === active?.area.id
            return (
              <button key={a.area.id} type="button" role="menuitem" onClick={() => { setOpen(false); onPick(a) }}
                className={`flex w-full items-center gap-2.5 rounded-[4px] px-2.5 py-2 text-left hover:bg-s-hebung ${on ? "bg-s-innen" : ""}`}>
                <AIcon size={16} className={`shrink-0 ${a.area.text}`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-bold text-[#e8eef8]">{a.area.title}</span>
                  <span className="block truncate text-[11px] text-[#9aa7bc]">{a.area.blurb}</span>
                </span>
                <span className="text-[11px] text-[#9aa7bc]">{a.items.length}</span>
              </button>
            )
          })}
        </div>
      </>}
    </div>
  )
}
