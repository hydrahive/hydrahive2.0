import { useEffect, useState } from "react"
import { GitBranch, GitCommitHorizontal, Loader2, ArrowUp, ArrowDown, Eye, EyeOff } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectGitStatus } from "./types"

interface Props {
  projectId: string
  gitInitialized: boolean
  remoteUrlSaved?: string | null
  onChanged?: () => void
}

type Busy = "" | "init" | "clone" | "remote" | "commit" | "push" | "pull"

export function GitTab({ projectId, gitInitialized, onChanged }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [status, setStatus] = useState<ProjectGitStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<Busy>("")
  const [error, setError] = useState<string | null>(null)

  const [cloneUrl, setCloneUrl] = useState("")
  const [cloneBranch, setCloneBranch] = useState("")
  const [remoteUrl, setRemoteUrl] = useState("")
  const [token, setToken] = useState("")
  const [showToken, setShowToken] = useState(false)
  const [commitMsg, setCommitMsg] = useState("")

  async function reload() {
    setLoading(true)
    try { setStatus(await projectsApi.getGit(projectId)) }
    catch { setStatus({ initialized: false }) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    reload()
    setCloneUrl(""); setCloneBranch(""); setRemoteUrl(""); setToken(""); setCommitMsg(""); setError(null)
  }, [projectId])

  useEffect(() => { setRemoteUrl(status?.remote_url ?? "") }, [status?.remote_url])

  async function run(b: Busy, fn: () => Promise<unknown>, after?: () => Promise<void> | void) {
    setBusy(b); setError(null)
    try { await fn(); if (after) await after(); else { await reload(); onChanged?.() } }
    catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
    finally { setBusy("") }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 size={20} className="animate-spin text-zinc-500" />
    </div>
  )

  const repoExists = gitInitialized && !!status?.initialized

  return (
    <div className="space-y-4">
      {error && <ErrorBox text={error} />}

      {!repoExists ? (
        <CloneOrInit
          cloneUrl={cloneUrl} setCloneUrl={setCloneUrl}
          cloneBranch={cloneBranch} setCloneBranch={setCloneBranch}
          token={token} setToken={setToken}
          showToken={showToken} setShowToken={setShowToken}
          busy={busy}
          onClone={() => run("clone", () => projectsApi.gitClone(projectId, {
            url: cloneUrl, branch: cloneBranch || undefined, token: token || undefined,
          }))}
          onInit={() => run("init", () => projectsApi.gitInit(projectId))}
          t={t}
        />
      ) : (
        <>
          <SettingsRow
            token={token} setToken={setToken}
            showToken={showToken} setShowToken={setShowToken}
            remoteUrl={remoteUrl} setRemoteUrl={setRemoteUrl}
            savedRemote={status?.remote_url ?? null}
            busy={busy === "remote"}
            onSave={() => run("remote", () =>
              projectsApi.putGitConfig(projectId, {
                remote_url: remoteUrl || undefined,
                git_token: token || undefined,
              })
            )}
            t={t}
          />
          <StatusPills status={status!} t={t} />
          <CommitPushPull
            commitMsg={commitMsg} setCommitMsg={setCommitMsg}
            busy={busy}
            ahead={status!.ahead ?? 0}
            hasRemote={!!status!.remote_url}
            onCommit={() => run("commit", () => projectsApi.gitCommit(projectId, commitMsg), async () => {
              setCommitMsg(""); await reload(); onChanged?.()
            })}
            onPush={() => run("push", () => projectsApi.gitPush(projectId))}
            onPull={() => run("pull", () => projectsApi.gitPull(projectId))}
            t={t}
          />
          <CommitsList commits={status!.commits ?? []} t={t} />
        </>
      )}
    </div>
  )
}

function ErrorBox({ text }: { text: string }) {
  return <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{text}</p>
}

function SettingsRow({ token, setToken, showToken, setShowToken, remoteUrl, setRemoteUrl, savedRemote, busy, onSave, t }: {
  token: string; setToken: (v: string) => void
  showToken: boolean; setShowToken: (v: boolean) => void
  remoteUrl: string; setRemoteUrl: (v: string) => void
  savedRemote: string | null
  busy: boolean; onSave: () => void
  t: (k: string) => string
}) {
  const dirty = remoteUrl !== (savedRemote ?? "") || token !== ""
  return (
    <div className="rounded-lg border border-white/[6%] bg-white/[2%] p-3 space-y-2">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.remote_url")}</label>
          <input value={remoteUrl} onChange={(e) => setRemoteUrl(e.target.value)}
            placeholder="https://github.com/owner/repo.git"
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </div>
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.token")}</label>
          <div className="flex gap-1">
            <input type={showToken ? "text" : "password"} value={token} onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_…"
              className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
            <button type="button" onClick={() => setShowToken(!showToken)}
              className="px-2 py-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
              {showToken ? <EyeOff size={12} /> : <Eye size={12} />}
            </button>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <p className="text-[10px] text-zinc-600">{t("git.token_hint")}</p>
        <button onClick={onSave} disabled={!dirty || busy}
          className="px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
          {busy ? <Loader2 size={11} className="animate-spin" /> : t("git.save_settings")}
        </button>
      </div>
    </div>
  )
}

function CloneOrInit({ cloneUrl, setCloneUrl, cloneBranch, setCloneBranch, token, setToken, showToken, setShowToken, busy, onClone, onInit, t }: {
  cloneUrl: string; setCloneUrl: (v: string) => void
  cloneBranch: string; setCloneBranch: (v: string) => void
  token: string; setToken: (v: string) => void
  showToken: boolean; setShowToken: (v: boolean) => void
  busy: Busy
  onClone: () => void; onInit: () => void
  t: (k: string) => string
}) {
  return (
    <div className="rounded-lg border border-white/[6%] bg-white/[2%] p-3 space-y-3">
      <p className="text-xs text-zinc-400 font-medium">{t("git.no_repo_yet")}</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-end">
        <div className="sm:col-span-2 space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.clone_url")}</label>
          <input value={cloneUrl} onChange={(e) => setCloneUrl(e.target.value)}
            placeholder="https://github.com/owner/repo.git"
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </div>
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.branch_optional")}</label>
          <input value={cloneBranch} onChange={(e) => setCloneBranch(e.target.value)}
            placeholder="main"
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </div>
      </div>
      <div className="space-y-0.5">
        <label className="block text-[10px] text-zinc-500">{t("git.token")}</label>
        <div className="flex gap-1">
          <input type={showToken ? "text" : "password"} value={token} onChange={(e) => setToken(e.target.value)}
            placeholder="ghp_…"
            className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
          <button type="button" onClick={() => setShowToken(!showToken)}
            className="px-2 py-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            {showToken ? <EyeOff size={12} /> : <Eye size={12} />}
          </button>
        </div>
        <p className="text-[10px] text-zinc-600">{t("git.token_hint_clone")}</p>
      </div>
      <div className="flex justify-end gap-2">
        <button onClick={onInit} disabled={busy !== ""}
          className="px-3 py-1 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-white/[8%] disabled:opacity-30">
          {busy === "init" ? <Loader2 size={11} className="animate-spin" /> : t("git.init_empty")}
        </button>
        <button onClick={onClone} disabled={!cloneUrl || busy !== ""}
          className="px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
          {busy === "clone" ? <Loader2 size={11} className="animate-spin" /> : t("git.clone")}
        </button>
      </div>
    </div>
  )
}

function StatusPills({ status, t }: { status: ProjectGitStatus; t: (k: string) => string }) {
  return (
    <div className="flex flex-wrap gap-2">
      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-500/[8%] border border-violet-500/20 text-xs text-violet-300">
        <GitBranch size={11} /> {status.branch}
      </span>
      {(status.ahead ?? 0) > 0 && (
        <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/[8%] border border-emerald-500/20 text-xs text-emerald-400">
          <ArrowUp size={11} /> {status.ahead} {t("git.ahead")}
        </span>
      )}
      {(status.behind ?? 0) > 0 && (
        <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/[8%] border border-amber-500/20 text-xs text-amber-400">
          <ArrowDown size={11} /> {status.behind} {t("git.behind")}
        </span>
      )}
    </div>
  )
}

function CommitPushPull({ commitMsg, setCommitMsg, busy, ahead, hasRemote, onCommit, onPush, onPull, t }: {
  commitMsg: string; setCommitMsg: (v: string) => void
  busy: Busy
  ahead: number
  hasRemote: boolean
  onCommit: () => void; onPush: () => void; onPull: () => void
  t: (k: string) => string
}) {
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input value={commitMsg} onChange={(e) => setCommitMsg(e.target.value)}
          placeholder={t("git.commit_message_placeholder")}
          className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
        <button onClick={onCommit} disabled={!commitMsg || busy !== ""}
          className="px-3 py-1 rounded-md bg-violet-600/80 hover:bg-violet-600 text-white text-xs font-medium disabled:opacity-30">
          {busy === "commit" ? <Loader2 size={11} className="animate-spin" /> : t("git.commit")}
        </button>
      </div>
      <div className="flex gap-2 justify-end">
        <button onClick={onPull} disabled={!hasRemote || busy !== ""}
          className="flex items-center gap-1 px-3 py-1 rounded-md text-xs text-zinc-300 hover:text-white hover:bg-white/5 border border-white/[8%] disabled:opacity-30">
          {busy === "pull" ? <Loader2 size={11} className="animate-spin" /> : <ArrowDown size={11} />}
          {t("git.pull")}
        </button>
        <button onClick={onPush} disabled={!hasRemote || busy !== "" || ahead === 0}
          className="flex items-center gap-1 px-3 py-1 rounded-md bg-emerald-600/80 hover:bg-emerald-600 text-white text-xs font-medium disabled:opacity-30">
          {busy === "push" ? <Loader2 size={11} className="animate-spin" /> : <ArrowUp size={11} />}
          {t("git.push")} {ahead > 0 && `(${ahead})`}
        </button>
      </div>
    </div>
  )
}

function CommitsList({ commits, t }: { commits: { hash: string; subject: string; author: string; date: string }[]; t: (k: string) => string }) {
  if (commits.length === 0) return null
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-medium text-zinc-500 mb-1">{t("git.recent_commits")}</p>
      {commits.map((c) => (
        <div key={c.hash} className="flex items-start gap-2.5 px-3 py-1.5 rounded-md bg-zinc-900 border border-white/[6%]">
          <GitCommitHorizontal size={12} className="text-zinc-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-zinc-300 truncate">{c.subject}</p>
            <p className="text-[10px] text-zinc-600">{c.author} · {c.date}</p>
          </div>
          <span className="text-[10px] text-zinc-600 font-mono flex-shrink-0">{c.hash}</span>
        </div>
      ))}
    </div>
  )
}
