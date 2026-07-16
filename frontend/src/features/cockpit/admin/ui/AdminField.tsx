import type { InputHTMLAttributes, ReactNode } from "react"
import { cn } from "@/shared/cn"

export const adminInputClass = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8] placeholder:text-[#5b6675] focus:border-[#69d7ff]/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"

interface FieldProps {
  label: ReactNode
  help?: ReactNode
  error?: ReactNode
  children: ReactNode
  className?: string
}

export function AdminField({ label, help, error, children, className }: FieldProps) {
  return (
    <label className={cn("block space-y-1.5", className)}>
      <span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">{label}</span>
      {children}
      {help && !error && <span className="block text-[11px] leading-relaxed text-[#5b6675]">{help}</span>}
      {error && <span className="block text-[11px] leading-relaxed text-rose-300">{error}</span>}
    </label>
  )
}

interface ToggleProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: ReactNode
}

export function AdminToggle({ label, className, ...props }: ToggleProps) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2", className)}>
      <span className="relative inline-flex h-6 w-11 shrink-0">
        <input type="checkbox" className="peer sr-only" {...props} />
        <span className="absolute inset-0 rounded-full border border-[#2a364b] bg-[#172133] transition-colors peer-checked:border-[#69d7ff]/50 peer-checked:bg-[#163248] peer-focus-visible:ring-2 peer-focus-visible:ring-[#69d7ff]/45 peer-disabled:opacity-40" />
        <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-[#8d9ab0] transition-all peer-checked:translate-x-5 peer-checked:bg-[#69d7ff]" />
      </span>
      {label && <span className="text-sm text-[#e8eef8]">{label}</span>}
    </label>
  )
}
