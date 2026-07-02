import type { CSSProperties, TextareaHTMLAttributes } from "react"
import { forwardRef } from "react"
import { cn } from "@/shared/cn"

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

const ctlStyle: CSSProperties = {
  borderRadius: "var(--hh-ctl-r)",
  paddingBlock: "var(--hh-ctl-py)",
  paddingInline: "var(--hh-ctl-px)",
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, className, style, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      {...rest}
      style={{ ...ctlStyle, ...style }}
      className={cn(
        "w-full bg-zinc-900/70 text-sm text-zinc-100 placeholder:text-zinc-600 resize-y",
        "border transition-colors focus:outline-none focus-visible:ring-2",
        invalid
          ? "border-red-500/60 focus-visible:ring-red-500/40"
          : "border-white/[10%] focus:border-[var(--hh-accent-border)] focus-visible:ring-[var(--hh-accent-border)]",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
    />
  )
})
