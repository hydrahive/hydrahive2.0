import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react"
import { cn } from "@/shared/cn"

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline"
export type ButtonSize = "sm" | "md" | "lg"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /** Icon links vom Label (lucide o.ä.). */
  icon?: ReactNode
  /** Voll-Breite. */
  block?: boolean
}

// Größen nutzen die Look-Control-Variablen als Basis (Dichte skaliert mit
// dem Look-Preset). sm/lg weichen relativ davon ab.
const sizeStyle: Record<ButtonSize, CSSProperties> = {
  sm: { paddingBlock: "calc(var(--hh-ctl-py) * 0.7)", paddingInline: "calc(var(--hh-ctl-px) * 0.75)" },
  md: { paddingBlock: "var(--hh-ctl-py)", paddingInline: "var(--hh-ctl-px)" },
  lg: { paddingBlock: "calc(var(--hh-ctl-py) * 1.3)", paddingInline: "calc(var(--hh-ctl-px) * 1.3)" },
}

const sizeText: Record<ButtonSize, string> = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-base",
}

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] text-white font-medium " +
    "shadow-lg shadow-black/30 hover:brightness-110",
  secondary:
    "bg-white/[6%] text-zinc-200 border border-white/[10%] hover:bg-white/[10%] hover:border-white/20",
  ghost:
    "text-zinc-400 hover:text-zinc-100 hover:bg-white/5",
  outline:
    "bg-transparent text-[var(--hh-accent-text)] border border-[var(--hh-accent-border)] " +
    "hover:bg-[var(--hh-accent-soft)]",
  danger:
    "bg-gradient-to-r from-red-600 to-rose-600 text-white font-medium shadow-lg shadow-black/30 hover:brightness-110",
}

export function Button({
  variant = "primary",
  size = "md",
  icon,
  block = false,
  className,
  style,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      style={{ borderRadius: "var(--hh-ctl-r)", ...sizeStyle[size], ...style }}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-medium leading-none",
        "transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hh-accent-border)]",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100",
        sizeText[size],
        variantClass[variant],
        block && "w-full",
        className,
      )}
    >
      {icon && <span className="shrink-0 [&>svg]:block">{icon}</span>}
      {children}
    </button>
  )
}
