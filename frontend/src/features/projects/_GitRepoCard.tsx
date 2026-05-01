import { useEffect, useState } from "react"
import {
  ArrowDown, ArrowUp, ChevronDown, ChevronRight, Eye, EyeOff,
  GitBranch, GitCommitHorizontal, Loader2, Settings, Trash2,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectGitRepo } from "./types"

interface Props {
  projectId: string
  repo: ProjectGitRepo
  onChanged: () => void | Promise<void>
}

type Busy = "" | "config" | "commit" | "push" | "pull" | "delete"

export function GitRepoCard({ projectId, repo, onChanged }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [open, setOpen] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [busy, setBusy] = useState<Busy>("")
  const [error, setError] = useState<string | null>(null)
  const [commitMsg, setCommitMsg] = useState("")
  const [remoteUrl, setRemoteUrl] = useState(repo.status.remote_url ?? "")
  const [token, setToken] = useState("")
  const [showToken, setShowToken] = useState(false)

  useEffect(() => { setRemoteUrl(repo.status.remote_url ?? "") }, [repo.status.remote_url])

  const isRoot = repo.name === "_root"
  const ahead = repo.status.ahead ?? 0
  const behind = repo.status.behind ?? 0
  const hasRemote = !!repo.status.remote_url

  async function run(b: Busy, fn: () => Promise<unknown>) {
    setBusy(b); setError(null)
    try { await fn(); await onChanged() }
    catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
    finally { setBusy("") }
  }

  async function deleteRepo() {
    if (!confirm(t("git.delete_confirm", { name: repo.name }))) return
    await run("delete", () => projectsApi.deleteRepo(projectId, repo.name))
  }

  return (
    <div className="rounded-lg border border-white/[8%] bg-white/[2%]">
      <div className="flex items-center gap-2 px-3 py-2">
        <button onClick={() => setOpen(!open)} className="text-zinc-500 hover:text-zinc-200">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <span className="text-sm font-mono text-zinc-200 flex-1">
          {repo.name}{isRoot && <span className="text-[10px] text-zinc-500 ml-2">(legacy)</span>}
        </span>
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-violet-500/[8%] border border-violet-500/20 text-[10px] text-violet-300">
          <GitBranch size={10} /> {repo.status.branch ?? "?"}
        </span>
        {ahead > 0 && (
          <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-emerald-500/[8%] border border-emerald-500/20 text-[10px] text-emerald-400">
            <ArrowUp size={9} /> {ahead}
          </span>
        )}
        {behind > 0 && (
          <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-amber-500/[8%] border border-amber-500/20 text-[10px] text-amber-400">
            <ArrowDown size={9} /> {behind}
          </span>
        )}
        <button onClick={() => setShowSettings(!showSettings)}
          className={`p-1 rounded ${showSettings ? "text-violet-300 bg-violet-500/10" : "text-zinc-500 hover:text-zinc-200 hover:bg-white/5"}`}>
          <Settings size={12} />
        </button>
        {!isRoot && (
          <button onClick={deleteRepo} disabled={busy !== ""}
            className="p-1 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30">
            {busy === "delete" ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
          </button>
        )}
      </div>

      {showSettings && (
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
              onClick={() => run("config", () => projectsApi.putRepoConfig(projectId, repo.name, {
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
              <button onClick={deleteRepo} disabled={busy !== ""}
                className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-rose-600/80 hover:bg-rose-600 text-white text-xs font-medium disabled:opacity-30">
                {busy === "delete" ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
                {t("git.delete_repo")}
              </button>
            </div>
          )}
        </div>
      )}

      {open && (
        <div className="border-t border-white/[6%] p-3 space-y-2">
          {error && (
            <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-2 py-1">{error}</p>
          )}
          <div className="flex gap-2">
            <input value={commitMsg} onChange={(e) => setCommitMsg(e.target.value)}
              placeholder={t("git.commit_message_placeholder")}
              className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
            <button onClick={() => run("commit", async () => {
                await projectsApi.commitRepo(projectId, repo.name, commitMsg)
                setCommitMsg("")
              })}
              disabled={!commitMsg || busy !== ""}
              className="px-3 py-1 rounded-md bg-violet-600/80 hover:bg-violet-600 text-white text-xs font-medium disabled:opacity-30">
              {busy === "commit" ? <Loader2 size={11} className="animate-spin" /> : t("git.commit")}
            </button>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => run("pull", () => projectsApi.pullRepo(projectId, repo.name))}
              disabled={!hasRemote || busy !== ""}
              className="flex items-center gap-1 px-3 py-1 rounded-md text-xs text-zinc-300 hover:text-white hover:bg-white/5 border border-white/[8%] disabled:opacity-30">
              {busy === "pull" ? <Loader2 size={11} className="animate-spin" /> : <ArrowDown size={11} />}
              {t("git.pull")}
            </button>
            <button
              onClick={() => run("push", () => projectsApi.pushRepo(projectId, repo.name))}
              disabled={!hasRemote || busy !== "" || ahead === 0}
              className="flex items-center gap-1 px-3 py-1 rounded-md bg-emerald-600/80 hover:bg-emerald-600 text-white text-xs font-medium disabled:opacity-30">
              {busy === "push" ? <Loader2 size={11} className="animate-spin" /> : <ArrowUp size={11} />}
              {t("git.push")} {ahead > 0 && `(${ahead})`}
            </button>
          </div>
          {(repo.status.commits?.length ?? 0) > 0 && (
            <div className="space-y-1 pt-1">
              <p className="text-[10px] font-medium text-zinc-500 mb-1">{t("git.recent_commits")}</p>
              {repo.status.commits!.map((c) => (
                <div key={c.hash} className="flex items-start gap-2 px-2 py-1 rounded-md bg-zinc-900 border border-white/[6%]">
                  <GitCommitHorizontal size={11} className="text-zinc-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-zinc-300 truncate">{c.subject}</p>
                    <p className="text-[10px] text-zinc-600">{c.author} · {c.date}</p>
                  </div>
                  <span className="text-[10px] text-zinc-600 font-mono flex-shrink-0">{c.hash}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
