import { useEffect, useState } from "react"
import { Coins } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

interface ModelUsage {
  name: string
  label: string
  interval_total: number
  interval_used: number
  interval_pct: number
  interval_reset_in_s: number
  weekly_total: number
  weekly_used: number
  weekly_pct: number
}

interface Usage {
  available: boolean
  reason?: string
  fetched_at: string
  models?: ModelUsage[]
}

const REFRESH_MS = 30_000

function fmtResetIn(s: number): string {
  if (s <= 0) return "—"
  const d = Math.floor(s / 86400)
  if (d > 0) return `${d}d ${Math.floor((s % 86400) / 3600)}h`
  const h = Math.floor(s / 3600)
  if (h > 0) return `${h}h ${Math.floor((s % 3600) / 60)}m`
  return `${Math.floor(s / 60)}m`
}

function pctTone(p: number): string {
  if (p >= 90) return "bg-rose-400"
  if (p >= 70) return "bg-amber-400"
  return "bg-emerald-400"
}

export function MinimaxUsageCard() {
  const { t } = useTranslation("system")
  const [usage, setUsage] = useState<Usage | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const r = await api.get<Usage>("/llm/minimax/usage")
        if (alive) setUsage(r)
      } catch { /* leise */ }
    }
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])

  if (!usage || (!usage.available && usage.reason === "no_api_key")) return null

  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Coins size={14} className="text-amber-300" />
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          {t("minimax.title")}
        </p>
      </div>

      {!usage.available ? (
        <p className="text-xs text-rose-300/80">{t(`minimax.error_${usage.reason}`, { defaultValue: usage.reason })}</p>
      ) : !usage.models || usage.models.length === 0 ? (
        <p className="text-xs text-zinc-500">{t("minimax.no_data")}</p>
      ) : (
        <div className="space-y-2">
          {usage.models.map((m) => (
            <div key={m.label} className="space-y-0.5">
              <div className="flex items-center gap-2 text-[11px]">
                <span className="font-mono text-zinc-300 truncate flex-1 min-w-0" title={m.label}>{m.label}</span>
                <span className="text-zinc-500 tabular-nums whitespace-nowrap">
                  {m.interval_used.toLocaleString()} / {m.interval_total.toLocaleString()}
                </span>
                <span className={`tabular-nums whitespace-nowrap font-mono text-[10px] ${m.interval_pct >= 90 ? "text-rose-300" : m.interval_pct >= 70 ? "text-amber-300" : "text-emerald-300"}`}>
                  {m.interval_pct}%
                </span>
              </div>
              <div className="h-1 bg-white/[5%] rounded-full overflow-hidden">
                <div className={`h-full transition-all ${pctTone(m.interval_pct)}`} style={{ width: `${m.interval_pct}%` }} />
              </div>
              <p className="text-[9.5px] text-zinc-600">
                {t("minimax.reset_in", { time: fmtResetIn(m.interval_reset_in_s) })}
                {m.weekly_total > 0 && (
                  <> · {t("minimax.weekly", { used: m.weekly_used.toLocaleString(), total: m.weekly_total.toLocaleString(), pct: m.weekly_pct })}</>
                )}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
