// Kasten ⊞: Suche und alle Apps nach Bereichen, der aktuelle Bereich oben (docs/specs/startdesktop.md).
import { useEffect, useRef, useState, type ReactNode } from "react"
import { Grid3X3, Search, X } from "lucide-react"
import type { NavItem } from "@/shared/nav-config"
import { orderForMenu, type FilledArea } from "./areaLogic"

interface Props {
  areas: FilledArea[]
  activeId: string | null
  label: (i: NavItem) => string
  onOpen: (path: string) => void
  /** Seitenknopf und Zusatzknöpfe – auf dem Handy hier, weil die Leiste dafür zu schmal ist. */
  action?: { label: string; path: string }
  extraActions?: ReactNode
}

export function AreaAppsMenu({ areas, activeId, label, onOpen, action, extraActions }: Props) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false) }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])

  const shown = orderForMenu(areas, activeId, q, label)
  const go = (path: string) => { setOpen(false); setQ(""); onOpen(path) }

  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label="Alle Apps" title="Alle Apps"
        className="rounded-[4px] border border-[#2a364b] bg-[#172133] p-2 text-[#e8eef8] hover:border-[#46617f]">
        <Grid3X3 size={16} />
      </button>
      {open && <>
        <button type="button" className="fixed inset-0 z-[119] cursor-default bg-black/40" aria-label="Apps schließen" onClick={() => setOpen(false)} />
        <section role="dialog" aria-label="Alle Apps"
          className="fixed inset-x-3 top-[64px] z-[120] max-h-[calc(100dvh-80px)] overflow-y-auto rounded-[6px] border border-[#2a364b] bg-[#101724] p-3 shadow-2xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-11 sm:w-[560px]">
          <div className="mb-3 flex items-center gap-2">
            <label className="flex min-w-0 flex-1 items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2.5 py-2">
              <Search size={14} className="shrink-0 text-[#8d9ab0]" />
              <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="App suchen …" aria-label="App suchen"
                onKeyDown={(e) => { if (e.key === "Enter" && shown[0]) go(shown[0].items[0].path) }}
                className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] placeholder:text-[#5f6d84] focus:outline-none" />
            </label>
            <button type="button" onClick={() => setOpen(false)} aria-label="Apps schließen" className="rounded p-2 text-[#8d9ab0] hover:bg-white/5 hover:text-white"><X size={16} /></button>
          </div>
          {(action || extraActions) && (
            <div className="mb-3 flex flex-wrap gap-2 border-b border-[#2a364b] pb-3 md:hidden">
              {action && <button type="button" onClick={() => go(action.path)}
                className="rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-1.5 text-xs font-bold text-[#e8eef8]">{action.label}</button>}
              {extraActions}
            </div>
          )}
          {shown.length === 0 && <p className="px-1 py-2 text-sm text-[#8d9ab0]">Nichts gefunden.</p>}
          {shown.map(({ area, items }) => {
            const Icon = area.icon
            return (
              <div key={area.id} className="mb-3 last:mb-0">
                <p className={`mb-1 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider ${area.text}`}>
                  <Icon size={12} /> {area.title}
                  {area.id === activeId && <span className="font-normal normal-case tracking-normal text-[#718097]">· hier bist du</span>}
                </p>
                <div className="grid grid-cols-2 gap-1 sm:grid-cols-3">
                  {items.map((i) => (
                    <button key={i.path} type="button" onClick={() => go(i.path)}
                      className="flex min-w-0 items-center gap-2 rounded-[4px] border border-transparent px-2 py-2 text-left text-xs text-[#b8c4d8] hover:border-[#2a364b] hover:bg-[#172133] hover:text-white">
                      <i.icon size={14} className={`shrink-0 ${area.text}`} /><span className="truncate">{label(i)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </section>
      </>}
    </div>
  )
}
