import type { CSSProperties, InputHTMLAttributes, ReactNode } from "react"
import { forwardRef } from "react"
import { cn } from "@/shared/cn"

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Icon links im Feld. */
  icon?: ReactNode
  /** Fehlerzustand (roter Rand). */
  invalid?: boolean
}

const ctlStyle: CSSProperties = {
  borderRadius: "var(--hh-ctl-r)",
  paddingBlock: "var(--hh-ctl-py)",
  paddingInline: "var(--hh-ctl-px)",
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { icon, invalid, className, style, ...rest },
  ref,
) {
  const field = (
    <input
      ref={ref}
      {...rest}
      style={{ ...ctlStyle, ...(icon ? { paddingInlineStart: "2.25rem" } : null), ...style }}
      className={cn(
        "w-full bg-zinc-900/70 text-sm text-zinc-100 placeholder:text-zinc-600",
        "border transition-colors focus:outline-none focus-visible:ring-2",
        invalid
          ? "border-red-500/60 focus-visible:ring-red-500/40"
          : "border-white/[10%] focus:border-[var(--hh-accent-border)] focus-visible:ring-[var(--hh-accent-border)]",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
    />
  )

  if (!icon) return field

  return (
    <div className="relative w-full">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 [&>svg]:block pointer-events-none">
        {icon}
      </span>
      {field}
    </div>
  )
})
