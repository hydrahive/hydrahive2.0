import { useEffect, useState } from "react"
import { MessageSquare, Zap, Activity, Clock, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectStats } from "./types"

interface Props {
  projectId: string
}

function MiniStat({ icon: Icon, label, value, sub }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string
}) {
  return (
    <div className="flex items-center gap-2 px-2.5 py-2 rounded-md bg-white/[2%] border border-white/[6%]">
      <Icon size={14} className="text-zinc-500 shrink-0" />
      <div className="min-w-0">
        <p className="text-sm font-bold text-zinc-100 leading-tight truncate">{value}</p>
        <p className="text-[10px] text-zinc-500 leading-tight truncate" title={sub ?? label}>{sub ?? label}</p>
      </div>
    </div>
  )
}

export function StatsTab({ projectId }: Props) {
  const { t, i18n } = useTranslation("projects")
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    projectsApi.getStats(projectId)
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return (
    <div className="flex items-center justify-center py-6">
      <Loader2 size={16} className="animate-spin text-zinc-500" />
    </div>
  )

  if (!stats) return <p className="text-xs text-zinc-500 py-4 text-center">{t("stats.unavailable")}</p>

  const fmtTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

  return (
    <div className="grid grid-cols-2 gap-2">
      <MiniStat icon={Activity} value={stats.total_sessions}
        label={t("stats.sessions")}
        sub={stats.active_sessions > 0 ? t("stats.sessions_active", { count: stats.active_sessions }) : t("stats.sessions")} />
      <MiniStat icon={MessageSquare} value={stats.total_messages} label={t("stats.messages")} />
      <MiniStat icon={Zap} value={fmtTokens(stats.total_tokens)} label={t("stats.tokens")} />
      <MiniStat icon={Clock}
        value={stats.last_activity ? new Date(stats.last_activity).toLocaleDateString(i18n.language) : "—"}
        label={t("stats.last_activity")} />
    </div>
  )
}
