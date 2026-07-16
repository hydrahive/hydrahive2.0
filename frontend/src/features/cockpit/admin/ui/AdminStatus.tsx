import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"
import { cn } from "@/shared/cn"

export type AdminStatusTone = "neutral" | "success" | "warning" | "danger"

const toneClasses: Record<AdminStatusTone, string> = {
  neutral: "border-[#2a364b] bg-[#172133] text-[#8d9ab0]",
  success: "border-emerald-500/25 bg-emerald-500/[8%] text-emerald-300",
  warning: "border-amber-500/25 bg-amber-500/[8%] text-amber-300",
  danger: "border-rose-500/25 bg-rose-500/[8%] text-rose-300",
}

const dotClasses: Record<AdminStatusTone, string> = {
  neutral: "bg-[#8d9ab0]",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  danger: "bg-rose-400",
}

interface Props {
  tone?: AdminStatusTone
  children: ReactNode
  icon?: LucideIcon
  dot?: boolean
  pulse?: boolean
  className?: string
}

export function AdminStatus({ tone = "neutral", children, icon: Icon, dot = false, pulse = false, className }: Props) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-[4px] border px-2 py-1 text-[10px] font-bold uppercase tracking-wider", toneClasses[tone], className)}>
      {Icon ? <Icon size={11} /> : dot ? <span className={cn("h-1.5 w-1.5 rounded-full", dotClasses[tone], pulse && "animate-pulse")} /> : null}
      {children}
    </span>
  )
}
