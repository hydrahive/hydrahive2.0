import { useEffect, useState } from "react"
import { Loader2, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { GitRepoCard } from "./_GitRepoCard"
import { AddRepoForm } from "./_AddRepoForm"
import type { ProjectGitRepo } from "./types"

interface Props {
  projectId: string
  onChanged?: () => void
}

export function GitTab({ projectId, onChanged }: Props) {
  const { t } = useTranslation("projects")
  const [repos, setRepos] = useState<ProjectGitRepo[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    setLoading(true); setError(null)
    try { setRepos(await projectsApi.getRepos(projectId)) }
    catch (e) {
      setError(e instanceof Error ? e.message : "")
      setRepos([])
    }
    finally { setLoading(false) }
  }

  useEffect(() => { reload(); setShowAdd(false) }, [projectId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500">
          {repos.length === 0 ? t("git.no_repos") : t("git.repos_count", { count: repos.length })}
        </p>
        {!showAdd && (
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-1 px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium">
            <Plus size={11} /> {t("git.add_repo")}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
      )}

      {showAdd && (
        <AddRepoForm
          projectId={projectId}
          existingNames={repos.map((r) => r.name)}
          onCancel={() => setShowAdd(false)}
          onAdded={async () => { setShowAdd(false); await reload(); onChanged?.() }}
        />
      )}

      {repos.map((repo) => (
        <GitRepoCard
          key={repo.name}
          projectId={projectId}
          repo={repo}
          onChanged={async () => { await reload(); onChanged?.() }}
        />
      ))}
    </div>
  )
}
