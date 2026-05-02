import { useEffect, useState } from "react"
import { Eye, EyeOff, Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectGitRepo } from "./types"

export type Busy = "" | "config" | "commit" | "push" | "pull" | "delete"

interface Props {
  projectId: string
  repo: ProjectGitRepo
  isRoot: boolean
  busy: Busy
  onRun: (b: Busy, fn: () => Promise<unknown>) => void
  onDelete: () => void
}

export function GitRepoSettings({ projectId, repo, isRoot, busy, onRun, onDelete }: Props) {
  const { t } = useTranslation("projects")
  const [remoteUrl, setRemoteUrl] = useState(repo.status.remote_url ?? "")
  const [token, setToken] = useState("")
  const [showToken, setShowToken] = useState(false)

  useEffect(() => { setRemoteUrl(repo.status.remote_url ?? "") }, [repo.status.remote_url])

  return (
    <div className="border-t border-white/[6%] p-3 space-y-3 bg-zinc-950/30">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.remote_url")}</label>
          <input value={remoteUrl} onChange={(e) => setRemoteUrl(e.target.value)}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </div>
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">
            {t("git.token")} {repo.has_token && <span className="text-zinc-600">· {t("git.token_set")}</span>}
          </label>
          <div className="flex gap-1">
            <input type={showToken ? "text" : "password"} value={token} onChange={(e) => setToken(e.target.value)}
              placeholder={repo.has_token ? "••••••••" : "ghp_…"}
              className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
            <button type="button" onClick={() => setShowToken(!showToken)}
              className="px-2 py-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
              {showToken ? <EyeOff size={12} /> : <Eye size={12} />}
            </button>
          </div>
        </div>
      </div>
      <div className="flex justify-end">
        <button
          onClick={() => onRun("config", () => projectsApi.putRepoConfig(projectId, repo.name, {
            remote_url: remoteUrl !== (repo.status.remote_url ?? "") ? remoteUrl : undefined,
            git_token: token || undefined,
          }))}
          disabled={busy !== "" || (remoteUrl === (repo.status.remote_url ?? "") && !token)}
          className="px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
          {busy === "config" ? <Loader2 size={11} className="animate-spin" /> : t("git.save_settings")}
        </button>
      </div>
      {!isRoot && (
        <div className="pt-3 border-t border-rose-500/20 flex items-center justify-between">
          <p className="text-[11px] text-rose-300/80">{t("git.danger_zone_hint")}</p>
          <button onClick={onDelete} disabled={busy !== ""}
            className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-rose-600/80 hover:bg-rose-600 text-white text-xs font-medium disabled:opacity-30">
            {busy === "delete" ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
            {t("git.delete_repo")}
          </button>
        </div>
      )}
    </div>
  )
}
