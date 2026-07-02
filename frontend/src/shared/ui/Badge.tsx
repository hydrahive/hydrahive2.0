import type { CSSProperties, HTMLAttributes, ReactNode } from "react"
import { cn } from "@/shared/cn"

export type BadgeVariant = "accent" | "neutral" | "success" | "warning" | "danger"

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  icon?: ReactNode
}

const variantClass: Record<BadgeVariant, string> = {
  accent: "bg-[var(--hh-accent-soft)] text-[var(--hh-accent-text)] border-[var(--hh-accent-border)]",
  neutral: "bg-white/[6%] text-zinc-300 border-white/[12%]",
  success: "bg-emerald-500/12 text-emerald-300 border-emerald-500/30",
  warning: "bg-amber-500/12 text-amber-300 border-amber-500/30",
  danger: "bg-red-500/12 text-red-300 border-red-500/30",
}

export function Badge({ variant = "neutral", icon, className, style, children, ...rest }: BadgeProps) {
  return (
    <span
      {...rest}
      style={{ borderRadius: "calc(var(--hh-ctl-r) * 1.6)", ...style } as CSSProperties}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium border leading-none",
        variantClass[variant],
        className,
      )}
    >
      {icon && <span className="[&>svg]:block">{icon}</span>}
      {children}
    </span>
  )
}
