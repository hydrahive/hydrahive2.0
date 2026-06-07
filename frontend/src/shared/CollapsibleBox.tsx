import { type CSSProperties, type ReactNode, useState } from "react"
import { ChevronDown } from "lucide-react"

/**
 * Einklappbare Inhaltsbox (SPEC-Konvention, Web-Konsole/Design).
 *
 * Standard-Box-Chrome (`.box` + `.box-h`-Header) + Einklapp-Button im Header. Der
 * Auf-/Zu-Zustand wird je `boxId` in localStorage persistiert (bleibt über Sessions/Tabs
 * erhalten — wie Theme/Sprache). Body wird vom Aufrufer geliefert (z.B. `.box-b` oder
 * `p-3`). Vorlage für jede künftige Box.
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
  /** Wird in den `.ic`-Chip des Headers gelegt (26px, `--c`-getönt). */
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
        className="box-h cursor-pointer select-none"
        style={collapsed ? { borderBottom: "none" } : undefined}
        onClick={toggle}
        aria-expanded={!collapsed}
        role="button"
      >
        {icon && <span className="ic">{icon}</span>}
        <span className="t">{title}</span>
        <span className="r flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {headerRight}
          <span
            aria-label={collapsed ? "Aufklappen" : "Einklappen"}
            className="text-zinc-500 hover:text-zinc-200 transition-colors"
          >
            <ChevronDown size={14} className={`transition-transform ${collapsed ? "-rotate-90" : ""}`} />
          </span>
        </span>
      </div>
      {!collapsed && children}
    </div>
  )
}
