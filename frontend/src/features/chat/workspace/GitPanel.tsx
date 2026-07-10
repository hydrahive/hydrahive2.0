import { useState, useEffect, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { gitApi, type GitStatus, type GitRepo } from "./api"

export function GitPanel({ agentId }: { agentId: string }) {
  const { t } = useTranslation("workspace")
  const [repos, setRepos] = useState<GitRepo[] | null>(null)
  const [repo, setRepo] = useState<string | null>(null)
  const [status, setStatus] = useState<GitStatus | null>(null)
  const [message, setMessage] = useState("")
  const [diff, setDiff] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Repos einmalig laden, erstes als Default wählen
  useEffect(() => {
    gitApi.repos(agentId)
      .then((rs) => { setRepos(rs); setRepo((cur) => cur ?? rs[0]?.name ?? null) })
      .catch(() => setRepos([]))
  }, [agentId])

  const refresh = useCallback(() => {
    if (!repo) return
    gitApi.status(agentId, repo).then(setStatus).catch(() => setStatus(null))
  }, [agentId, repo])

  useEffect(() => {
    if (!repo) return
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [repo, refresh])

  if (repos === null) return <div className="p-2 text-[11px] text-zinc-600">{t("loading")}</div>
  if (repos.length === 0) return <div className="p-2 text-[11px] text-zinc-600">{t("no_repo")}</div>

  async function doCommit() {
    if (!repo) return
    setBusy(true)
    try {
      await gitApi.commit(agentId, repo, message)
      setMessage(""); setDiff(null); refresh()
    } finally { setBusy(false) }
  }

  return (
    <div className="flex h-full flex-col bg-[#151c2b] text-[11px] text-[#e8eef8]">
      {/* Repo-Picker (nur bei mehreren) + Branch */}
      <div className="flex items-center gap-2 border-b border-[#2a364b] bg-[#121a29] px-2 py-1.5">
        {repos.length > 1 ? (
          <select value={repo ?? ""} onChange={(e) => { setRepo(e.target.value); setStatus(null); setDiff(null) }}
            className="max-w-[60%] rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-1.5 py-0.5 text-[10px] text-[#e8eef8]">
            {repos.map((r) => (
              <option key={r.name} value={r.name}>{r.name === "_root" ? "/" : r.name}</option>
            ))}
          </select>
        ) : (
          <span className="text-[#4ade80]">⎇ {status?.branch ?? repos[0]?.branch}</span>
        )}
        <span className="text-zinc-500 ml-auto">{status ? t("changed", { count: status.files.length }) : ""}</span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {status?.files.map((f) => (
          <div key={f.path} className="flex items-center gap-1.5 border-b border-[#223048] px-2 py-1 hover:bg-[#172133]">
            <input type="checkbox" checked={f.staged} className="accent-violet-500 shrink-0"
              onChange={(e) => repo && gitApi.stage(agentId, repo, f.path, e.target.checked).then(refresh).catch(() => {})} />
            <span className={`font-mono shrink-0 w-5 text-center ${f.status === "M" ? "text-amber-400" : f.status === "??" ? "text-emerald-400" : "text-zinc-400"}`}>
              {f.status || "·"}
            </span>
            <button onClick={() => repo && gitApi.diff(agentId, repo, f.path).then((r) => setDiff(r.diff)).catch(() => {})}
              className="truncate text-zinc-400 hover:text-zinc-200 text-left flex-1">{f.path}</button>
          </div>
        ))}
      </div>
      {diff !== null && (
        <pre className="max-h-40 overflow-auto border-t border-[#2a364b] bg-[#0d1420] px-2 py-1 font-mono text-[10px] text-[#8d9ab0] whitespace-pre-wrap">{diff || "—"}</pre>
      )}
      <div className="flex flex-col gap-1.5 border-t border-[#2a364b] bg-[#111827] p-2">
        <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder={t("commit_message")}
          className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1 text-[10px] text-[#e8eef8] outline-none focus:border-[#46617f]" />
        <button disabled={busy || !message.trim() || !status?.files.some((f) => f.staged)}
          onClick={doCommit}
          className="rounded-[4px] bg-gradient-to-br from-[#1fb6ff] to-[#8b5cf6] px-2 py-1 text-[10px] font-bold text-white hover:brightness-110 disabled:opacity-40">
          {t("commit")}
        </button>
      </div>
    </div>
  )
}
