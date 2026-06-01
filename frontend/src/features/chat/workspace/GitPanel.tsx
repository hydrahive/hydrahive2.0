import { useState, useEffect, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { gitApi, type GitStatus } from "./api"

export function GitPanel({ agentId }: { agentId: string }) {
  const { t } = useTranslation("workspace")
  const [status, setStatus] = useState<GitStatus | null>(null)
  const [message, setMessage] = useState("")
  const [diff, setDiff] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(() => {
    gitApi.status(agentId).then(setStatus).catch(() => setStatus(null))
  }, [agentId])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [refresh])

  if (!status) return <div className="p-2 text-[11px] text-zinc-600">{t("loading")}</div>
  if (!status.is_repo) return <div className="p-2 text-[11px] text-zinc-600">{t("no_repo")}</div>

  async function doCommit() {
    setBusy(true)
    try {
      await gitApi.commit(agentId, message)
      setMessage(""); setDiff(null); refresh()
    } finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col h-full text-[11px]">
      <div className="px-2 py-1.5 border-b border-white/[6%] flex items-center gap-2">
        <span className="text-emerald-400">⎇ {status.branch}</span>
        <span className="text-zinc-500 ml-auto">{t("changed", { count: status.files.length })}</span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {status.files.map((f) => (
          <div key={f.path} className="flex items-center gap-1.5 px-2 py-1 hover:bg-white/[3%]">
            <input type="checkbox" checked={f.staged} className="accent-violet-500 shrink-0"
              onChange={(e) => gitApi.stage(agentId, f.path, e.target.checked).then(refresh).catch(() => {})} />
            <span className={`font-mono shrink-0 w-5 text-center ${f.status === "M" ? "text-amber-400" : f.status === "??" ? "text-emerald-400" : "text-zinc-400"}`}>
              {f.status || "·"}
            </span>
            <button onClick={() => gitApi.diff(agentId, f.path).then((r) => setDiff(r.diff)).catch(() => {})}
              className="truncate text-zinc-400 hover:text-zinc-200 text-left flex-1">{f.path}</button>
          </div>
        ))}
      </div>
      {diff !== null && (
        <pre className="max-h-40 overflow-auto px-2 py-1 text-[10px] font-mono bg-black/30 border-t border-white/[6%] text-zinc-400 whitespace-pre-wrap">{diff || "—"}</pre>
      )}
      <div className="border-t border-white/[6%] p-2 flex flex-col gap-1.5">
        <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder={t("commit_message")}
          className="bg-zinc-900 border border-white/[8%] rounded px-2 py-1 text-[10px] text-zinc-200 outline-none focus:border-violet-500/50" />
        <button disabled={busy || !message.trim() || !status.files.some((f) => f.staged)}
          onClick={doCommit}
          className="px-2 py-1 rounded bg-violet-500/15 text-violet-300 text-[10px] disabled:opacity-40 hover:bg-violet-500/25">
          {t("commit")}
        </button>
      </div>
    </div>
  )
}
