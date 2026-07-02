import type { CSSProperties, SelectHTMLAttributes } from "react"
import { forwardRef } from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/shared/cn"

type SelectProps = SelectHTMLAttributes<HTMLSelectElement>

const ctlStyle: CSSProperties = {
  borderRadius: "var(--hh-ctl-r)",
  paddingBlock: "var(--hh-ctl-py)",
  paddingInline: "var(--hh-ctl-px)",
  paddingInlineEnd: "2.25rem",
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, style, children, ...rest },
  ref,
) {
  return (
    <div className="relative w-full">
      <select
        ref={ref}
        {...rest}
        style={{ ...ctlStyle, ...style }}
        className={cn(
          "w-full appearance-none bg-zinc-900/70 text-sm text-zinc-100",
          "border border-white/[10%] transition-colors focus:outline-none",
          "focus:border-[var(--hh-accent-border)] focus-visible:ring-2 focus-visible:ring-[var(--hh-accent-border)]",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          className,
        )}
      >
        {children}
      </select>
      <ChevronDown
        size={15}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none"
      />
    </div>
  )
})
