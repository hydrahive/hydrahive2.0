import { useEffect, useState } from "react"
import { MessageSquare, Zap, Activity, Clock, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectStats } from "./types"

interface Props {
  projectId: string
}

function StatCard({ icon: Icon, label, value, sub }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string
}) {
  return (
    <div className="p-4 rounded-xl bg-zinc-900 border border-white/[6%] space-y-2">
      <div className="flex items-center gap-2 text-zinc-500">
        <Icon size={13} />
        <span className="text-xs uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-zinc-600">{sub}</p>}
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
    <div className="flex items-center justify-center py-16">
      <Loader2 size={20} className="animate-spin text-zinc-500" />
    </div>
  )

  if (!stats) return <p className="text-sm text-zinc-500 py-8 text-center">{t("stats.unavailable")}</p>

  const fmtTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard icon={Activity} label={t("stats.sessions")} value={stats.total_sessions}
        sub={stats.active_sessions > 0 ? t("stats.sessions_active", { count: stats.active_sessions }) : undefined} />
      <StatCard icon={MessageSquare} label={t("stats.messages")} value={stats.total_messages} />
      <StatCard icon={Zap} label={t("stats.tokens")} value={fmtTokens(stats.total_tokens)} />
      <StatCard icon={Clock} label={t("stats.last_activity")}
        value={stats.last_activity
          ? new Date(stats.last_activity).toLocaleDateString(i18n.language)
          : "—"} />
    </div>
  )
}
