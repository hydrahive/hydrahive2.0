import type { ButtonHTMLAttributes } from "react"
import { cn } from "@/shared/cn"

type Tone = "default" | "primary" | "danger"

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: Tone
}

export function CockpitButton({ tone = "default", className, ...props }: Props) {
  return (
    <button
      {...props}
      className={cn(
        "rounded-[4px] border px-3 py-1.5 text-xs font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        tone === "primary" && "border-cyan-400/30 bg-cyan-400/15 text-cyan-100 hover:bg-cyan-400/20",
        tone === "danger" && "border-rose-400/30 bg-rose-500/10 text-rose-200 hover:bg-rose-500/15",
        tone === "default" && "border-white/[10%] bg-white/[4%] text-zinc-300 hover:bg-white/[7%] hover:text-zinc-100",
        className,
      )}
    />
  )
}
