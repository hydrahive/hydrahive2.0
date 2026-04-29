import { CheckCircle, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { HealthCheck } from "./api"

export function HealthBar({ checks }: { checks: HealthCheck[] }) {
  const { t } = useTranslation("system")
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {checks.map((c, i) => {
        const Icon = c.ok ? CheckCircle : XCircle
        const tone = c.ok
          ? "border-emerald-500/20 bg-emerald-500/[5%] text-emerald-300"
          : "border-rose-500/20 bg-rose-500/[5%] text-rose-300"
        const name = c.name_code ? t(`checks.${c.name_code}`) : (c.name ?? "?")
        const detail = c.detail_code
          ? t(`checks.${c.detail_code}`, c.params ?? {})
          : (c.detail ?? "")
        return (
          <div key={c.name_code ?? c.name ?? i} className={`rounded-xl border p-3 ${tone}`}>
            <div className="flex items-center gap-2">
              <Icon size={14} />
              <p className="text-xs font-semibold uppercase tracking-wider">{name}</p>
            </div>
            <p className="text-xs text-zinc-400 mt-1.5 leading-snug truncate" title={detail}>
              {detail}
            </p>
          </div>
        )
      })}
    </div>
  )
}
