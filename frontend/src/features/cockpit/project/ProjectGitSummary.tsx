import { useCallback, useEffect, useState } from "react"
import { CockpitButton } from "../CockpitButton"
import { projectsApi } from "@/features/projects/api"
import type { ProjectGitRepo } from "@/features/projects/types"

type GitAction = "pull" | "push"

interface Props {
  projectId: string | null
}

export function ProjectGitSummary({ projectId }: Props) {
  const [repos, setRepos] = useState<ProjectGitRepo[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [busyAction, setBusyAction] = useState<GitAction | null>(null)
  const [message, setMessage] = useState<string | null>(null)
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
      setError("Git-Status konnte nicht geladen werden.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { void reload() }, [reload])

  async function runAction(action: GitAction) {
    if (!projectId || !selectedRepo) return
    setBusyAction(action)
    setMessage(null)
    setError(null)
    try {
      if (action === "pull") await projectsApi.pullRepo(projectId, selectedRepo)
      if (action === "push") await projectsApi.pushRepo(projectId, selectedRepo)
      setMessage(action === "pull" ? "Pull abgeschlossen." : "Push abgeschlossen.")
      await reload()
    } catch {
      setError(action === "pull" ? "Pull fehlgeschlagen." : "Push fehlgeschlagen.")
    } finally {
      setBusyAction(null)
    }
  }

  const activeRepo = repos.find((repo) => repo.name === selectedRepo) ?? null
  const status = activeRepo?.status ?? null
  const canPull = Boolean(projectId && activeRepo?.status.initialized && (status?.behind ?? 0) > 0)
  const canPush = Boolean(projectId && activeRepo?.status.initialized && (status?.ahead ?? 0) > 0 && activeRepo?.has_token)

  return (
    <div>
      <div className="mb-3 flex justify-end"><CockpitButton disabled={!projectId || loading} onClick={() => void reload()}>Refresh</CockpitButton></div>
      {loading ? <p className="text-sm text-[#8d9ab0]">Lade Git-Status…</p> : null}
      {!loading && repos.length === 0 ? <p className="text-sm text-zinc-600">Keine Repos im Projekt.</p> : null}
      {error ? <p className="mb-2 text-xs text-rose-300">{error}</p> : null}
      {message ? <p className="mb-2 text-xs text-emerald-300">{message}</p> : null}

      {repos.length > 0 ? (
        <div className="space-y-2">
          <select
            value={selectedRepo ?? ""}
            onChange={(event) => setSelectedRepo(event.target.value || null)}
            className="w-full rounded-[4px] border border-white/[10%] bg-zinc-950/70 px-2 py-1.5 text-xs font-semibold text-zinc-300 outline-none hover:border-cyan-400/30"
          >
            {repos.map((repo) => <option key={repo.name} value={repo.name}>{repo.name}</option>)}
          </select>

          {activeRepo && status ? (
            <div className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-2">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-bold text-zinc-200">{activeRepo.name}</span>
                <span className={status.initialized ? "text-[11px] font-semibold text-emerald-300" : "text-[11px] font-semibold text-amber-300"}>
                  {status.initialized ? "git aktiv" : "kein git"}
                </span>
              </div>
              <p className="mt-0.5 truncate text-[11px] text-zinc-600">
                {status.branch ?? "—"} · ↑{status.ahead ?? 0} ↓{status.behind ?? 0}
              </p>
              {status.commits && status.commits.length > 0 ? (
                <div className="mt-2 space-y-1 border-t border-white/[6%] pt-2">
                  {status.commits.slice(0, 3).map((commit) => (
                    <p key={commit.hash} className="truncate text-[11px] text-zinc-500">
                      <span className="font-mono text-zinc-400">{commit.hash.slice(0, 7)}</span> {commit.subject}
                    </p>
                  ))}
                </div>
              ) : null}
              <div className="mt-3 flex gap-2">
                <CockpitButton disabled={!canPull || busyAction !== null} onClick={() => void runAction("pull")}>Pull</CockpitButton>
                <CockpitButton disabled={!canPush || busyAction !== null} onClick={() => void runAction("push")}>Push</CockpitButton>
              </div>
              {!activeRepo.has_token ? <p className="mt-2 text-[11px] text-zinc-600">Push benötigt ein hinterlegtes Git-Token.</p> : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="mt-3 rounded-[4px] border border-rose-400/20 bg-rose-500/[5%] p-2 text-xs text-zinc-400">
        Gitea: noch nicht eingerichtet · Repo erstellen folgt in eigener Etappe.
      </div>
    </div>
  )
}
