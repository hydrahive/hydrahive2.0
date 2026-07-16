import { cn } from "@/shared/cn"

export function RadioCard({ active, onClick, title, desc }: {
  active: boolean
  onClick: () => void
  title: string
  desc: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-[4px] border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/45",
        active
          ? "border-[#69d7ff]/60 bg-[#163248]"
          : "border-[#2a364b] bg-[#111827] hover:border-[#46617f]",
      )}
    >
      <p className="text-sm font-medium text-[#e8eef8]">{title}</p>
      <p className="mt-0.5 text-[11px] text-[#8d9ab0]">{desc}</p>
    </button>
  )
}
