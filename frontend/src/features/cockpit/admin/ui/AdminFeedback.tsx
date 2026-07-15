import type { ReactNode } from "react"
import { AlertCircle, CheckCircle, Info, Loader2, TriangleAlert } from "lucide-react"
import { cn } from "@/shared/cn"
import type { AdminStatusTone } from "./AdminStatus"

const styles: Record<AdminStatusTone, string> = {
  neutral: "border-[#2a364b] bg-[#131b2a] text-[#8d9ab0]",
  success: "border-emerald-500/25 bg-emerald-500/[7%] text-emerald-300",
  warning: "border-amber-500/25 bg-amber-500/[7%] text-amber-300",
  danger: "border-rose-500/25 bg-rose-500/[7%] text-rose-300",
}

const icons = { neutral: Info, success: CheckCircle, warning: TriangleAlert, danger: AlertCircle }

export function AdminFeedback({ tone = "neutral", children, loading = false, className }: { tone?: AdminStatusTone; children: ReactNode; loading?: boolean; className?: string }) {
  const Icon = loading ? Loader2 : icons[tone]
  return (
    <div className={cn("flex items-start gap-2 rounded-[4px] border px-3 py-2 text-xs leading-relaxed", styles[tone], className)}>
      <Icon size={14} className={cn("mt-0.5 shrink-0", loading && "animate-spin")} />
      <div className="min-w-0">{children}</div>
    </div>
  )
}

export function AdminCodeBlock({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <pre className={cn("overflow-auto whitespace-pre-wrap rounded-[4px] border border-[#2a364b] bg-[#080d15] p-3 font-mono text-[11px] leading-relaxed text-[#b9c5d6]", className)}>
      {children}
    </pre>
  )
}
