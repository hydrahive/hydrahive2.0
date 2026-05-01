import { Bot, Crown, MessageSquare, Wrench } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import type { DashboardSession } from "./api"

const TYPE_ICON = { master: Crown, project: Bot, specialist: Wrench }

interface Props {
  sessions: DashboardSession[]
}

export function RecentSessions({ sessions }: Props) {
  const { t } = useTranslation("dashboard")

  function relativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime()
    const min = Math.floor(diff / 60_000)
    if (min < 1) return t("just_now")
    if (min < 60) return t("minutes_ago", { count: min })
    const hours = Math.floor(min / 60)
    if (hours < 24) return t("hours_ago", { count: hours })
    const days = Math.floor(hours / 24)
    return t("days_ago", { count: days })
  }

  if (sessions.length === 0) {
    return (
      <SectionShell title={t("sections.recent_sessions")}>
        <p className="text-xs text-zinc-500 py-4 text-center">{t("sections.recent_sessions_empty")}</p>
      </SectionShell>
    )
  }
  return (
    <SectionShell title={t("sections.recent_sessions")}>
      <div className="space-y-0.5 max-h-[180px] overflow-y-auto pr-1">
        {sessions.map((s) => {
          const Icon = (s.agent_type && TYPE_ICON[s.agent_type as keyof typeof TYPE_ICON]) || MessageSquare
          return (
            <Link key={s.id} to={`/chat?session=${s.id}`}
              className="flex items-center gap-2 px-1.5 py-1 rounded-md hover:bg-white/[4%] transition-colors">
              <div className="w-5 h-5 rounded-full bg-gradient-to-br from-indigo-500/30 to-violet-600/30 flex items-center justify-center flex-shrink-0">
                <Icon size={10} className="text-violet-300" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-zinc-200 truncate leading-tight">{s.title || `Session ${s.id.slice(0, 8)}`}</p>
                <p className="text-[10px] text-zinc-600 truncate leading-tight">{s.agent_name}</p>
              </div>
              <span className="text-[10px] text-zinc-600 flex-shrink-0">{relativeTime(s.updated_at)}</span>
            </Link>
          )
        })}
      </div>
    </SectionShell>
  )
}

function SectionShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-4">
      <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">{title}</h3>
      {children}
    </div>
  )
}
