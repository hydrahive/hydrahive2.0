import type { ReactNode } from "react"
import { cn } from "@/shared/cn"
import { BoxHead } from "@/shared/brand/BoxHead"
import { BOX_THEMES, type BoxTheme } from "@/shared/brand/boxThemes"

interface Props {
  title?: string
  eyebrow?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Thema der Box: fester Hydra-Kopf links im Kopf + feiner Verlauf in dessen Farbe. */
  theme?: BoxTheme
}

export function CockpitPanel({ title, eyebrow, actions, children, className, theme }: Props) {
  return (
    <section data-box-theme={theme}
      className={cn("min-h-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3 text-[#e8eef8]",
        theme && `bg-gradient-to-b ${BOX_THEMES[theme].wash} to-[#151c2b] to-[90px]`, className)}>
      {(title || eyebrow || actions || theme) && (
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            {theme && <BoxHead theme={theme} />}
            <div className="min-w-0">
            {eyebrow && <CockpitSectionLabel>{eyebrow}</CockpitSectionLabel>}
            {title && <h2 className="truncate text-sm font-bold text-[#e8eef8]">{title}</h2>}
            </div>
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

export function CockpitSectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-1 inline-flex rounded-[4px] border border-[#69d7ff]/35 bg-[#1c2940] px-2 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#69d7ff]">
      {children}
    </p>
  )
}
