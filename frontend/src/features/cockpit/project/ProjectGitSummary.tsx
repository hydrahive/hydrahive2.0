import { useEffect, useState } from "react"
import { CockpitButton } from "../CockpitButton"
import { CockpitPanel } from "../CockpitPanel"
import { projectsApi } from "@/features/projects/api"
import type { ProjectGitRepo } from "@/features/projects/types"

interface Props {
  projectId: string | null
}

export function ProjectGitSummary({ projectId }: Props) {
  const [repos, setRepos] = useState<ProjectGitRepo[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let alive = true
    if (!projectId) {
      setRepos([])
      return
    }
    setLoading(true)
    projectsApi.getRepos(projectId)
      .then((r) => { if (alive) setRepos(r) })
      .catch(() => { if (alive) setRepos([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [projectId])

  return (
    <CockpitPanel title="Git Status" eyebrow="Git" actions={<CockpitButton disabled={!projectId}>Diff</CockpitButton>}>
      {loading ? <p className="text-sm text-zinc-600">Lade Git-Status…</p> : null}
      {!loading && repos.length === 0 ? <p className="text-sm text-zinc-600">Keine Repos im Projekt.</p> : null}
      <div className="space-y-2">
        {repos.slice(0, 4).map((repo) => {
          const status = repo.status
          const dirty = status.initialized && ((status.ahead ?? 0) > 0 || (status.behind ?? 0) > 0)
          return (
            <div key={repo.name} className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-2">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-bold text-zinc-200">{repo.name}</span>
                <span className={dirty ? "text-[11px] font-semibold text-amber-300" : "text-[11px] font-semibold text-emerald-300"}>
                  {dirty ? "sync" : status.initialized ? "sauber" : "kein git"}
                </span>
              </div>
              <p className="mt-0.5 truncate text-[11px] text-zinc-600">
                {status.branch ?? "—"} · ↑{status.ahead ?? 0} ↓{status.behind ?? 0}
              </p>
            </div>
          )
        })}
      </div>
      <div className="mt-3 rounded-[4px] border border-rose-400/20 bg-rose-500/[5%] p-2 text-xs text-zinc-400">
        Gitea: noch nicht eingerichtet · Repo erstellen folgt in eigener Etappe.
      </div>
    </CockpitPanel>
  )
}
