import { useEffect, useState } from "react"
import { MessageSquare, Loader2, ExternalLink } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectSession } from "./types"

interface Props {
  projectId: string
}

export function SessionsTab({ projectId }: Props) {
  const { t, i18n } = useTranslation("projects")
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<ProjectSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    projectsApi.getSessions(projectId)
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 size={20} className="animate-spin text-zinc-500" />
    </div>
  )

  if (!sessions.length) return (
    <p className="text-sm text-zinc-500 py-8 text-center">{t("sessions.empty")}</p>
  )

  return (
    <div className="space-y-1.5">
      {sessions.map((s) => (
        <button
          key={s.id}
          onClick={() => navigate(`/chat/${s.id}`)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[6%] hover:border-violet-500/30 hover:bg-violet-500/[4%] transition-all group text-left"
        >
          <MessageSquare size={14} className="text-zinc-500 group-hover:text-violet-400 flex-shrink-0" />
          <span className="flex-1 text-sm text-zinc-300 truncate">{s.title || t("sessions.untitled")}</span>
          <span className="text-xs text-zinc-600 flex-shrink-0">
            {new Date(s.updated_at).toLocaleDateString(i18n.language)}
          </span>
          <ExternalLink size={11} className="text-zinc-600 group-hover:text-violet-400 flex-shrink-0" />
        </button>
      ))}
    </div>
  )
}
