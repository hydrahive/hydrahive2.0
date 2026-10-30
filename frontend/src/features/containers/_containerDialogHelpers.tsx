import { cn } from "@/shared/cn"

export function RadioCard({ active, onClick, title, desc, disabled }: {
  active: boolean
  onClick: () => void
  title: string
  desc: string
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={cn(
        "rounded-[4px] border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/45 disabled:cursor-not-allowed disabled:opacity-40",
        active
          ? "border-[#69d7ff]/60 bg-[#163248]"
          : "border-s-rand bg-s-innen hover:border-s-rand-hover",
      )}
    >
      <p className="text-sm font-medium text-[#e8eef8]">{title}</p>
      <p className="mt-0.5 text-[11px] text-[#9aa7bc]">{desc}</p>
    </button>
  )
}
