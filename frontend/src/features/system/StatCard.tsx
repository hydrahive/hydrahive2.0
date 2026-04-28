import type { LucideIcon } from "lucide-react"

interface Props {
  icon: LucideIcon
  label: string
  value: string | number
  detail?: string
  glow: string  // tailwind shadow-* class for the violet/indigo glow
}

export function StatCard({ icon: Icon, label, value, detail, glow }: Props) {
  return (
    <div className={`relative rounded-2xl border border-white/[8%] bg-gradient-to-br from-white/[3%] to-transparent p-5 overflow-hidden`}>
      <div className={`absolute -top-8 -right-8 w-24 h-24 rounded-full blur-2xl opacity-40 ${glow}`} />
      <div className="relative">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-white/[5%] border border-white/[6%] flex items-center justify-center">
            <Icon size={14} className="text-zinc-300" />
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{label}</p>
        </div>
        <p className="text-2xl font-bold text-white tabular-nums">{value}</p>
        {detail && <p className="text-xs text-zinc-500 mt-1">{detail}</p>}
      </div>
    </div>
  )
}
