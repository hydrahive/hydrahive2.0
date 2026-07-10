import type { ReactNode } from "react"
import { cn } from "@/shared/cn"

interface Props {
  title?: string
  eyebrow?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

export function CockpitPanel({ title, eyebrow, actions, children, className }: Props) {
  return (
    <section className={cn("min-h-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3 text-[#e8eef8]", className)}>
      {(title || eyebrow || actions) && (
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {eyebrow && <CockpitSectionLabel>{eyebrow}</CockpitSectionLabel>}
            {title && <h2 className="truncate text-sm font-bold text-[#e8eef8]">{title}</h2>}
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
