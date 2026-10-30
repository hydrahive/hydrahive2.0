import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"
import { cn } from "@/shared/cn"

interface Props {
  icon: LucideIcon
  label: ReactNode
  value: ReactNode
  detail?: ReactNode
  className?: string
}

export function AdminStat({ icon: Icon, label, value, detail, className }: Props) {
  return (
    <div className={cn("rounded-[6px] border border-s-rand bg-s-innen p-4", className)}>
      <div className="mb-3 flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-[4px] border border-s-rand bg-s-innen text-[#69d7ff]">
          <Icon size={14} />
        </span>
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9aa7bc]">{label}</p>
      </div>
      <p className="text-2xl font-black tabular-nums text-[#e8eef8]">{value}</p>
      {detail && <p className="mt-1 text-xs leading-relaxed text-[#9aa7bc]">{detail}</p>}
    </div>
  )
}
