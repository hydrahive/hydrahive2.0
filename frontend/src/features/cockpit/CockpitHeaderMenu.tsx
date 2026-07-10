import type { ComponentType } from "react"
import { cn } from "@/shared/cn"

export interface CockpitMenuItem {
  label: string
  path: string
  icon?: ComponentType<{ size?: number; className?: string }>
  active?: boolean
  primary?: boolean
}

interface Props {
  items: CockpitMenuItem[]
  compact?: boolean
}

export function CockpitHeaderMenu({ items, compact = false }: Props) {
  return (
    <nav className="flex min-w-0 flex-wrap items-center gap-1.5" aria-label="Cockpit-Menü">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <button
            key={`${item.path}-${item.label}`}
            onClick={() => window.open(item.path, "_self")}
            className={cn(
              "inline-flex items-center gap-2 rounded-[4px] border px-2.5 py-1.5 text-xs font-bold transition-colors",
              compact ? "px-2 py-1 text-[11px]" : null,
              item.primary
                ? "border-[#69d7ff]/45 bg-[#1c2940] text-[#e8eef8] hover:bg-[#233653]"
                : item.active
                  ? "border-[#69d7ff]/35 bg-[#111d2d] text-[#69d7ff]"
                  : "border-[#2a364b] bg-[#111827] text-[#8d9ab0] hover:border-[#46617f] hover:bg-[#172133] hover:text-[#e8eef8]",
            )}
          >
            {Icon ? <Icon size={compact ? 12 : 14} className="shrink-0" /> : null}
            <span>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
