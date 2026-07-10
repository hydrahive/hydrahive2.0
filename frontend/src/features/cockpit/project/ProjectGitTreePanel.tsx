import { useCallback, useEffect, useState } from "react"
import { GitBranch } from "lucide-react"
import { CockpitButton } from "../CockpitButton"
import { CockpitPanel, CockpitSectionLabel } from "../CockpitPanel"
import { projectsApi } from "@/features/projects/api"
import type { ProjectGitRepo } from "@/features/projects/types"

interface Props {
  projectId: string | null
}

export function ProjectGitTreePanel({ projectId }: Props) {
  const [repos, setRepos] = useState<ProjectGitRepo[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!projectId) {
      setRepos([])
      setSelectedRepo(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const next = await projectsApi.getRepos(projectId)
      setRepos(next)
      setSelectedRepo((cur) => cur && next.some((repo) => repo.name === cur) ? cur : (next[0]?.name ?? null))
    } catch {
      setRepos([])
      setSelectedRepo(null)
      setError("Git Tree konnte nicht geladen werden.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { void reload() }, [reload])

  const activeRepo = repos.find((repo) => repo.name === selectedRepo) ?? repos[0] ?? null
  const status = activeRepo?.status ?? null
  const commits = status?.commits ?? []

  return (
    <CockpitPanel className="flex min-h-0 flex-col p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <CockpitSectionLabel>Git Tree</CockpitSectionLabel>
          <h2 className="truncate text-sm font-bold text-[#e8eef8]">{activeRepo?.name ?? "Repository"}</h2>
        </div>
        <CockpitButton disabled={!projectId || loading} onClick={() => void reload()}>
          <GitBranch size={12} className="mr-1 inline" /> Branch
        </CockpitButton>
      </div>

      {repos.length > 1 && (
        <select
          value={selectedRepo ?? ""}
          onChange={(event) => setSelectedRepo(event.target.value || null)}
          className="mb-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-xs font-semibold text-[#e8eef8] outline-none hover:border-[#46617f]"
        >
          {repos.map((repo) => <option key={repo.name} value={repo.name}>{repo.name}</option>)}
        </select>
      )}

      {error ? <p className="text-xs text-rose-300">{error}</p> : null}
      {loading ? <p className="text-xs text-[#8d9ab0]">Lade Git Tree…</p> : null}
      {!loading && !activeRepo ? <p className="text-xs text-[#8d9ab0]">Kein Repository im Projekt.</p> : null}

      {activeRepo && (
        <div className="min-h-0 flex-1 overflow-y-auto rounded-[4px] border border-[#223048] bg-[#111827] p-2 font-mono text-xs leading-6 text-[#cdd7e6]">
          <div className="mb-1 flex items-center gap-2 text-[#69d7ff]">
            <span>{status?.branch ?? "—"}</span>
            {status?.ahead || status?.behind ? <span className="text-[10px] text-[#8d9ab0]">↑{status?.ahead ?? 0} ↓{status?.behind ?? 0}</span> : null}
          </div>
          {commits.length > 0 ? (
            commits.slice(0, 8).map((commit, index) => (
              <div key={commit.hash} className="truncate">
                <span className="text-[#8d9ab0]">{index === commits.length - 1 ? "└─" : "├─"}</span>{" "}
                <span className="text-[#69d7ff]">{commit.hash.slice(0, 8)}</span>{" "}
                <span>{commit.subject}</span>
              </div>
            ))
          ) : (
            <div className="text-[#8d9ab0]">└─ keine Commits verfügbar</div>
          )}
        </div>
      )}
    </CockpitPanel>
  )
}
