import { useEffect, useState } from "react"
import { GitBranch, GitCommitHorizontal, Loader2, ArrowUp, ArrowDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectGitStatus } from "./types"

interface Props {
  projectId: string
  gitInitialized: boolean
}

export function GitTab({ projectId, gitInitialized }: Props) {
  const { t } = useTranslation("projects")
  const [status, setStatus] = useState<ProjectGitStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    projectsApi.getGit(projectId)
      .then(setStatus)
      .catch(() => setStatus({ initialized: false }))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 size={20} className="animate-spin text-zinc-500" />
    </div>
  )

  if (!gitInitialized || !status?.initialized) return (
    <p className="text-sm text-zinc-500 py-8 text-center">{t("git.not_initialized")}</p>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-500/[8%] border border-violet-500/20 text-xs text-violet-300">
          <GitBranch size={11} /> {status.branch}
        </span>
        {(status.ahead ?? 0) > 0 && (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/[8%] border border-emerald-500/20 text-xs text-emerald-400">
            <ArrowUp size={11} /> {status.ahead} ahead
          </span>
        )}
        {(status.behind ?? 0) > 0 && (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/[8%] border border-amber-500/20 text-xs text-amber-400">
            <ArrowDown size={11} /> {status.behind} behind
          </span>
        )}
      </div>

      {status.remote_url && (
        <p className="text-xs text-zinc-500 font-mono truncate px-0.5">{status.remote_url}</p>
      )}

      {(status.commits?.length ?? 0) > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">{t("git.recent_commits")}</p>
          {status.commits!.map((c) => (
            <div key={c.hash} className="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-zinc-900 border border-white/[6%]">
              <GitCommitHorizontal size={13} className="text-zinc-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-300 truncate">{c.subject}</p>
                <p className="text-xs text-zinc-600">{c.author} · {c.date}</p>
              </div>
              <span className="text-xs text-zinc-600 font-mono flex-shrink-0">{c.hash}</span>
            </div>
          ))}
        </div>
      )}

      {!status.remote_url && (status.ahead ?? 0) === 0 && (status.behind ?? 0) === 0 && (
        <p className="text-xs text-zinc-600">{t("git.no_remote")}</p>
      )}
    </div>
  )
}
