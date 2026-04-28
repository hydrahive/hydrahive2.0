import { CheckCircle, XCircle } from "lucide-react"
import type { HealthCheck } from "./api"

export function HealthBar({ checks }: { checks: HealthCheck[] }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {checks.map((c) => {
        const Icon = c.ok ? CheckCircle : XCircle
        const tone = c.ok
          ? "border-emerald-500/20 bg-emerald-500/[5%] text-emerald-300"
          : "border-rose-500/20 bg-rose-500/[5%] text-rose-300"
        return (
          <div key={c.name} className={`rounded-xl border p-3 ${tone}`}>
            <div className="flex items-center gap-2">
              <Icon size={14} />
              <p className="text-xs font-semibold uppercase tracking-wider">{c.name}</p>
            </div>
            <p className="text-xs text-zinc-400 mt-1.5 leading-snug truncate" title={c.detail}>
              {c.detail}
            </p>
          </div>
        )
      })}
    </div>
  )
}
