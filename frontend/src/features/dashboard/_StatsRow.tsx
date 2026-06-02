import { Activity, Coins, MessageSquare, Server } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
import type { CSSProperties } from "react"
import type { DashboardStats } from "./api"

interface Props {
  stats: DashboardStats
}

export function StatsRow({ stats }: Props) {
  const { t } = useTranslation("dashboard")
  const cards = [
    {
      icon: MessageSquare,
      label: t("stats.active_sessions"),
      value: stats.active_sessions,
      from: "from-fuchsia-500", to: "to-fuchsia-700",
      c: "217 70 239",
    },
    {
      icon: Coins,
      label: t("stats.tokens_today"),
      value: formatNumber(stats.tokens_today),
      from: "from-amber-500", to: "to-orange-600",
      c: "245 158 11",
    },
    {
      icon: Activity,
      label: t("stats.tool_calls_today"),
      value: formatNumber(stats.tool_calls_today),
      from: "from-emerald-500", to: "to-teal-600",
      c: "16 185 129",
    },
    {
      icon: Server,
      label: t("stats.servers_running"),
      value: stats.servers_running,
      detail: stats.servers_total > 0
        ? t("stats.servers_total_suffix", { total: stats.servers_total })
        : undefined,
      from: "from-teal-500", to: "to-sky-600",
      c: "20 184 166",
    },
  ]
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div key={c.label}
          className="box group relative px-3.5 py-3 flex items-center gap-2.5"
          style={{ "--c": c.c } as CSSProperties}>
          <div className={cn(
            "relative w-7 h-7 rounded-full flex items-center justify-center bg-gradient-to-br shrink-0",
            c.from, c.to,
          )}>
            <c.icon size={13} className="text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-zinc-500 text-[9px] uppercase tracking-wide truncate">{c.label}</p>
            <p className="text-base font-bold text-white leading-tight">
              {c.value}
              {c.detail && <span className="text-[10px] font-normal text-zinc-600 ml-1.5">{c.detail}</span>}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

function formatNumber(n: number): string {
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`
  return `${(n / 1_000_000).toFixed(1)}M`
}
