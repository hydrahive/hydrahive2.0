import { forwardRef, type ButtonHTMLAttributes } from "react"
import { cn } from "@/shared/cn"

type Tone = "default" | "primary" | "danger"

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: Tone
}

export const CockpitButton = forwardRef<HTMLButtonElement, Props>(function CockpitButton(
  { tone = "default", className, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      {...props}
      className={cn(
        "rounded-[4px] border px-3 py-1.5 text-xs font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        tone === "primary" && "border-[#69d7ff]/45 bg-[#163248] text-[#c8f2ff] hover:border-[#69d7ff]/70 hover:bg-[#1b3d56]",
        tone === "danger" && "border-rose-400/30 bg-rose-500/10 text-rose-200 hover:bg-rose-500/15",
        tone === "default" && "border-[#2a364b] bg-[#172133] text-[#e8eef8] hover:border-[#46617f] hover:bg-[#1b2536]",
        className,
      )}
    />
  )
})
