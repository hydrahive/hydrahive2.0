import { cn } from "@/shared/cn"

export type AdminActionTone = "default" | "primary" | "danger" | "ghost"

export function adminActionClass(tone: AdminActionTone = "default", className?: string) {
  return cn(
    "inline-flex items-center justify-center gap-1.5 rounded-[4px] border px-3 py-1.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/45 disabled:cursor-not-allowed disabled:opacity-40",
    tone === "default" && "border-[#2a364b] bg-[#172133] text-[#e8eef8] hover:border-[#46617f] hover:bg-[#1b2536]",
    tone === "primary" && "border-[#69d7ff]/45 bg-[#163248] text-[#c8f2ff] hover:border-[#69d7ff]/70 hover:bg-[#1b3d56]",
    tone === "danger" && "border-rose-400/30 bg-rose-500/10 text-rose-200 hover:bg-rose-500/15",
    tone === "ghost" && "border-transparent bg-transparent text-[#8d9ab0] hover:bg-[#172133] hover:text-[#e8eef8]",
    className,
  )
}
