import type { BuddyDecorVariant } from "./api"

const VARIANT_CLASS: Record<BuddyDecorVariant, string> = {
  default: "bg-[radial-gradient(circle_at_20%_10%,rgba(16,78,139,0.34),transparent_34%),radial-gradient(circle_at_78%_18%,rgba(124,58,237,0.22),transparent_28%),linear-gradient(145deg,rgba(15,23,42,0.58),rgba(2,6,23,0.18))]",
  calm: "bg-[radial-gradient(circle_at_22%_12%,rgba(20,184,166,0.22),transparent_32%),radial-gradient(circle_at_80%_82%,rgba(59,130,246,0.16),transparent_34%),linear-gradient(145deg,rgba(15,23,42,0.55),rgba(2,6,23,0.2))]",
  aurora: "bg-[radial-gradient(circle_at_15%_18%,rgba(52,211,153,0.25),transparent_30%),radial-gradient(circle_at_70%_8%,rgba(217,70,239,0.24),transparent_32%),radial-gradient(circle_at_85%_76%,rgba(59,130,246,0.2),transparent_30%)]",
  minimal: "bg-[linear-gradient(160deg,rgba(255,255,255,0.035),rgba(255,255,255,0.008))]",
}

export function BuddyDecorLayer({ variant }: { variant: BuddyDecorVariant }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className={`absolute inset-0 ${VARIANT_CLASS[variant] ?? VARIANT_CLASS.default}`} />
      <div className="absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      <div className="absolute -left-20 top-24 h-48 w-48 border border-sky-400/10 rotate-12" />
      <div className="absolute -right-16 bottom-20 h-36 w-36 border border-violet-400/10 -rotate-12" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.018)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.014)_1px,transparent_1px)] bg-[size:36px_36px] opacity-40" />
    </div>
  )
}
