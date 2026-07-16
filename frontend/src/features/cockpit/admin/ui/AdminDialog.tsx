import { useId, type ReactNode } from "react"
import { X } from "lucide-react"
import { cn } from "@/shared/cn"

interface Props {
  title: ReactNode
  eyebrow?: ReactNode
  icon?: ReactNode
  children: ReactNode
  footer?: ReactNode
  onClose?: () => void
  closeLabel?: string
  maxWidthClass?: string
  className?: string
}

export function AdminDialog({ title, eyebrow, icon, children, footer, onClose, closeLabel = "Schließen", maxWidthClass = "max-w-2xl", className }: Props) {
  const titleId = useId()
  return (
    <div className="fixed inset-0 z-[70] grid place-items-center bg-black/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <section className={cn("flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#0e1420] shadow-2xl", maxWidthClass, className)}>
        <header className="flex shrink-0 items-center gap-3 border-b border-[#2a364b] bg-[#131b2a] px-4 py-3">
          {icon && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-[4px] border border-[#2a364b] bg-[#172133] text-[#69d7ff]">{icon}</span>}
          <div className="min-w-0 flex-1">
            {eyebrow && <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#69d7ff]">{eyebrow}</p>}
            <h2 id={titleId} className="text-lg font-black text-[#e8eef8]">{title}</h2>
          </div>
          {onClose && (
            <button type="button" onClick={onClose} className="rounded-[4px] p-2 text-[#8d9ab0] hover:bg-[#172133] hover:text-[#e8eef8]" aria-label={closeLabel}>
              <X size={16} />
            </button>
          )}
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-4">{children}</main>
        {footer && <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-[#2a364b] bg-[#0b111c] px-4 py-3">{footer}</footer>}
      </section>
    </div>
  )
}
