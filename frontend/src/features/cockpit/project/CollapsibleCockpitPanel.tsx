import { ChevronDown, ChevronRight } from "lucide-react"
import type { ReactNode } from "react"
import { BoxHead } from "@/shared/brand/BoxHead"
import { BoxStatusSchild } from "@/shared/brand/BoxStatus"
import { boxLook, boxRahmenStil, kopfTonStil, type BoxStatus } from "@/shared/brand/boxLook"
import type { BoxTheme } from "@/shared/brand/boxThemes"
import { CockpitSectionLabel } from "../CockpitPanel"

interface Props {
  title: string
  eyebrow: string
  summary?: ReactNode
  collapsed: boolean
  onToggle: () => void
  children: ReactNode
  className?: string
  /** Thema der Box: fester Hydra-Kopf + Streifen in dessen Farbe (wie CockpitPanel). */
  theme?: BoxTheme
  /** Zustand: Warnung/Fehler übermalen die Kopffarbe, „ok“ zeigt nur das Schild. */
  status?: BoxStatus
}

export function CollapsibleCockpitPanel({ title, eyebrow, summary, collapsed, onToggle, children, className, theme, status }: Props) {
  const look = boxLook(theme, status)
  return (
    <section data-box-theme={theme} style={boxRahmenStil(look)} className={[
      "min-h-0 overflow-hidden rounded-[6px] border border-s-rand bg-s-box text-[#e8eef8]", className,
    ].filter(Boolean).join(" ")}>
      <button
        type="button"
        onClick={onToggle}
        style={kopfTonStil(look)}
        className="flex w-full items-center gap-3 bg-s-kopf px-3 py-2 text-left transition-colors hover:bg-s-hebung"
        aria-expanded={!collapsed}
      >
        {theme && <BoxHead theme={theme} />}
        <div className="min-w-0 flex-1">
          <CockpitSectionLabel farbe={look.streifen}>{eyebrow}</CockpitSectionLabel>
          <div className="flex min-w-0 items-center gap-2">
            {collapsed ? <ChevronRight size={14} className="shrink-0 text-[#9aa7bc]" /> : <ChevronDown size={14} className="shrink-0 text-[#69d7ff]" />}
            <h2 className="truncate text-sm font-bold text-[#e8eef8]">{title}</h2>
          </div>
          {summary ? <div className="mt-1 truncate text-[11px] text-[#9aa7bc]">{summary}</div> : null}
        </div>
        {look.schild && <BoxStatusSchild status={look.schild} />}
      </button>
      {!collapsed && <div className="border-t border-s-rand p-3">{children}</div>}
    </section>
  )
}
