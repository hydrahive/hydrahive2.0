import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"
import { cn } from "@/shared/cn"

interface Props {
  title?: ReactNode
  description?: ReactNode
  icon?: LucideIcon
  actions?: ReactNode
  children?: ReactNode
  className?: string
  bodyClassName?: string
}

export function AdminPanel({ title, description, icon: Icon, actions, children, className, bodyClassName }: Props) {
  const hasHeader = title || description || Icon || actions
  return (
    <section className={cn("overflow-hidden rounded-[6px] border border-s-rand bg-s-innen", className)}>
      {hasHeader && (
        <header className="flex items-start gap-3 border-b border-s-rand bg-s-kopf px-4 py-3">
          {Icon && (
            <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-[4px] border border-s-rand bg-s-innen text-[#69d7ff]">
              <Icon size={14} />
            </span>
          )}
          <div className="min-w-0 flex-1">
            {title && <h3 className="text-sm font-bold text-[#e8eef8]">{title}</h3>}
            {description && <p className="mt-0.5 text-xs leading-relaxed text-[#9aa7bc]">{description}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      {children && <div className={cn("p-4", bodyClassName)}>{children}</div>}
    </section>
  )
}
