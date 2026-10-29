import { ChevronDown, ChevronRight } from "lucide-react"
import type { ReactNode } from "react"
import { BoxHead } from "@/shared/brand/BoxHead"
import { BOX_THEMES, type BoxTheme } from "@/shared/brand/boxThemes"
import { CockpitSectionLabel } from "../CockpitPanel"

interface Props {
  title: string
  eyebrow: string
  summary?: ReactNode
  collapsed: boolean
  onToggle: () => void
  children: ReactNode
  className?: string
  /** Thema der Box: fester Hydra-Kopf + feiner Verlauf (wie CockpitPanel, Task 0dda5420). */
  theme?: BoxTheme
}

export function CollapsibleCockpitPanel({ title, eyebrow, summary, collapsed, onToggle, children, className, theme }: Props) {
  return (
    <section data-box-theme={theme} className={[
      "min-h-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b] text-[#e8eef8]",
      theme && `bg-gradient-to-b ${BOX_THEMES[theme].wash} to-[#151c2b] to-[90px]`, className,
    ].filter(Boolean).join(" ")}>
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 p-3 text-left transition-colors hover:bg-[#172133]"
        aria-expanded={!collapsed}
      >
        {theme && <BoxHead theme={theme} />}
        <div className="min-w-0 flex-1">
          <CockpitSectionLabel>{eyebrow}</CockpitSectionLabel>
          <div className="flex min-w-0 items-center gap-2">
            {collapsed ? <ChevronRight size={14} className="shrink-0 text-[#8d9ab0]" /> : <ChevronDown size={14} className="shrink-0 text-[#69d7ff]" />}
            <h2 className="truncate text-sm font-bold text-[#e8eef8]">{title}</h2>
          </div>
          {summary ? <div className="mt-1 truncate text-[11px] text-[#8d9ab0]">{summary}</div> : null}
        </div>
      </button>
      {!collapsed && <div className="border-t border-[#2a364b] p-3">{children}</div>}
    </section>
  )
}
