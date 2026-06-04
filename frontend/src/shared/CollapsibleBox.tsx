import { type CSSProperties, type ReactNode, useState } from "react"
import { ChevronDown } from "lucide-react"

/**
 * Einklappbare Inhaltsbox (SPEC-Konvention, Web-Konsole/Design).
 *
 * Standard-Box-Chrome (Rahmen + Header) + Einklapp-Button im Header. Der Auf-/Zu-
 * Zustand wird je `boxId` in localStorage persistiert (bleibt über Sessions/Tabs
 * erhalten — wie Theme/Sprache). Vorlage für jede künftige Box.
 */

const lsKey = (id: string) => `hh2.box.${id}`

function readCollapsed(id: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(lsKey(id))
    return v === null ? fallback : v === "1"
  } catch {
    return fallback
  }
}

interface Props {
  /** Stabiler Schlüssel für die Persistenz (eindeutig je Box). */
  boxId: string
  title: ReactNode
  icon?: ReactNode
  /** Optionaler Inhalt rechts im Header (z.B. ein Link) — vor dem Einklapp-Button. */
  headerRight?: ReactNode
  /** rgbFor()-Wert für das Glow-System (`--c`). */
  color?: string
  defaultCollapsed?: boolean
  /** Zusätzliche Klassen am Box-Container (z.B. "w-60"). */
  className?: string
  children: ReactNode
}

export function CollapsibleBox({
  boxId, title, icon, headerRight, color, defaultCollapsed = false, className = "", children,
}: Props) {
  const [collapsed, setCollapsed] = useState(() => readCollapsed(boxId, defaultCollapsed))

  const toggle = () =>
    setCollapsed((c) => {
      const next = !c
      try { localStorage.setItem(lsKey(boxId), next ? "1" : "0") } catch { /* ignore */ }
      return next
    })

  return (
    <div
      className={`box overflow-hidden ${className}`}
      style={color ? ({ "--c": color } as CSSProperties) : undefined}
    >
      <div
        className={`px-4 py-3 bg-black/20 flex items-center gap-2 ${collapsed ? "" : "border-b border-white/[6%]"}`}
      >
        {icon}
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex-1 min-w-0 truncate">
          {title}
        </span>
        {headerRight}
        <button
          type="button"
          onClick={toggle}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Aufklappen" : "Einklappen"}
          className="shrink-0 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ChevronDown size={14} className={`transition-transform ${collapsed ? "-rotate-90" : ""}`} />
        </button>
      </div>
      {!collapsed && children}
    </div>
  )
}
