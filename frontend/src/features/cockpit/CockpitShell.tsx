import type { ReactNode } from "react"
import { cn } from "@/shared/cn"

interface Props {
  title: string
  eyebrow?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

export function CockpitShell({ title, eyebrow, description, actions, children, className }: Props) {
  return (
    <div className={cn("min-h-full space-y-4", className)}>
      <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          {eyebrow && (
            <p className="inline-flex rounded-[4px] border border-cyan-400/25 bg-cyan-400/10 px-2 py-1 text-[11px] font-black uppercase tracking-[0.16em] text-cyan-200">
              {eyebrow}
            </p>
          )}
          <h1 className="mt-2 truncate text-2xl font-black tracking-tight text-zinc-100">{title}</h1>
          {description && <p className="mt-1 max-w-3xl text-sm text-zinc-500">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </header>
      {children}
    </div>
  )
}
