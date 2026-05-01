import { Activity, Coins, MessageSquare, Server } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
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
      glow: "hover:shadow-fuchsia-500/15",
    },
    {
      icon: Coins,
      label: t("stats.tokens_today"),
      value: formatNumber(stats.tokens_today),
      from: "from-amber-500", to: "to-orange-600",
      glow: "hover:shadow-amber-500/15",
    },
    {
      icon: Activity,
      label: t("stats.tool_calls_today"),
      value: formatNumber(stats.tool_calls_today),
      from: "from-emerald-500", to: "to-teal-600",
      glow: "hover:shadow-emerald-500/15",
    },
    {
      icon: Server,
      label: t("stats.servers_running"),
      value: stats.servers_running,
      detail: stats.servers_total > 0
        ? t("stats.servers_total_suffix", { total: stats.servers_total })
        : undefined,
      from: "from-teal-500", to: "to-sky-600",
      glow: "hover:shadow-teal-500/15",
    },
  ]
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
      {cards.map((c) => (
        <div key={c.label}
          className={cn(
            "group relative rounded-lg border border-white/[8%] bg-white/[3%] px-3 py-2 flex items-center gap-2.5",
            "hover:border-white/20 hover:bg-white/[6%] transition-all duration-200",
            c.glow,
          )}>
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
