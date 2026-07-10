import type { ReactNode } from "react"
import { cn } from "@/shared/cn"

interface Props {
  title: string
  eyebrow?: string
  description?: string
  actions?: ReactNode
  menu?: ReactNode
  children: ReactNode
  className?: string
  hideHeader?: boolean
}

export function CockpitShell({ title, eyebrow, description, actions, menu, children, className, hideHeader = false }: Props) {
  return (
    <div className={cn("min-h-full space-y-4", className)}>
      {!hideHeader && (
        <header className="shrink-0 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            {eyebrow && (
              <p className="inline-flex rounded-[4px] border border-[#69d7ff]/35 bg-[#1c2940] px-2 py-1 text-[11px] font-black uppercase tracking-[0.16em] text-[#69d7ff]">
                {eyebrow}
              </p>
            )}
            <h1 className="mt-2 truncate text-2xl font-black tracking-tight text-[#e8eef8]">{title}</h1>
            {description && <p className="mt-1 max-w-3xl text-sm text-[#8d9ab0]">{description}</p>}
            {menu && <div className="mt-3">{menu}</div>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </div>
  )
}
