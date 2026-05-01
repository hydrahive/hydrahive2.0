import { useEffect, useRef, useState } from "react"
import { CheckCircle2, Copy, Eye, EyeOff, FolderOpen, Loader2, Play, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { systemApi } from "./api"

type Phase = "idle" | "running" | "done" | "failed"

export function SambaCard() {
  const { t } = useTranslation("system")
  const { t: tCommon } = useTranslation("common")
  const [status, setStatus] = useState<Awaited<ReturnType<typeof systemApi.sambaStatus>> | null>(null)
  const [phase, setPhase] = useState<Phase>("idle")
  const [log, setLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showPwd, setShowPwd] = useState(false)
  const [copied, setCopied] = useState(false)
  const logRef = useRef<HTMLPreElement>(null)

  async function reload() {
    try { setStatus(await systemApi.sambaStatus()) }
    catch { /* leise */ }
  }

  useEffect(() => { reload() }, [])

  useEffect(() => {
    if (phase !== "running") return
    let alive = true
    async function pull() {
      try {
        const r = await systemApi.sambaLog(200)
        if (!alive) return
        if (r.exists) setLog(r.lines)
      } catch { /* ignore */ }
    }
    pull()
    const t = setInterval(pull, 1500)
    return () => { alive = false; clearInterval(t) }
  }, [phase])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  async function start() {
    setPhase("running"); setError(null); setLog([])
    try { await systemApi.sambaSetup() }
    catch (e) { setPhase("failed"); setError(e instanceof Error ? e.message : ""); return }
    const startedAt = Date.now()
    while (Date.now() - startedAt < 90_000) {
      await new Promise((r) => setTimeout(r, 2000))
      try {
        const s = await systemApi.sambaStatus()
        if (s.installed && s.running) {
          setStatus(s); setPhase("done"); return
        }
      } catch { /* ignore */ }
    }
    setPhase("failed"); setError(t("samba.timeout"))
  }

  async function copyPassword() {
    if (!status?.password) return
    await navigator.clipboard.writeText(status.password)
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-3">
      <div className="flex items-center gap-3">
        <FolderOpen size={16} className="text-amber-300 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-zinc-200">{t("samba.title")}</p>
          <p className="text-[11px] text-zinc-500 mt-0.5">{t("samba.subtitle")}</p>
        </div>
        {status && (
          status.installed && status.running ? (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/[8%] border border-emerald-500/20 text-[10px] text-emerald-300">
              <CheckCircle2 size={10} /> {t("samba.running")}
            </span>
          ) : (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/[8%] border border-amber-500/20 text-[10px] text-amber-300">
              <XCircle size={10} /> {t("samba.not_installed")}
            </span>
          )
        )}
      </div>

      {status?.installed && status.password_set && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
          <span className="text-zinc-500">{t("samba.user")}</span>
          <span className="text-zinc-300 font-mono">{status.user}</span>
          <span className="text-zinc-500">{t("samba.password")}</span>
          <span className="flex items-center gap-1.5">
            <span className="text-zinc-300 font-mono truncate flex-1">
              {showPwd ? status.password : "••••••••••••"}
            </span>
            <button onClick={() => setShowPwd(!showPwd)}
              className="p-0.5 text-zinc-500 hover:text-zinc-300">
              {showPwd ? <EyeOff size={11} /> : <Eye size={11} />}
            </button>
            <button onClick={copyPassword}
              className="p-0.5 text-zinc-500 hover:text-zinc-300"
              title={copied ? t("samba.copied") : t("samba.copy")}>
              {copied ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
            </button>
          </span>
        </div>
      )}

      {!status?.installed && phase === "idle" && (
        <button onClick={start}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white text-xs font-medium">
          <Play size={11} /> {t("samba.setup")}
        </button>
      )}

      {(phase === "running" || phase === "done" || phase === "failed") && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            {phase === "running" && (
              <><Loader2 size={12} className="animate-spin text-amber-300" /><span className="text-amber-300">{t("samba.running_setup")}</span></>
            )}
            {phase === "done" && (
              <><CheckCircle2 size={12} className="text-emerald-400" /><span className="text-emerald-300">{t("samba.done")}</span></>
            )}
            {phase === "failed" && (
              <><XCircle size={12} className="text-rose-400" /><span className="text-rose-300">{error ?? t("samba.failed")}</span></>
            )}
            {(phase === "done" || phase === "failed") && (
              <button onClick={() => { setPhase("idle"); setLog([]) }}
                className="ml-auto p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
                <X size={11} />
              </button>
            )}
          </div>
          <pre ref={logRef}
            className="rounded-md border border-white/[6%] bg-zinc-950 p-2 text-[11px] font-mono leading-relaxed text-zinc-300 overflow-x-auto whitespace-pre-wrap min-h-[120px] max-h-[260px]">
            {log.length > 0 ? log.join("") : <span className="text-zinc-600">{tCommon("status.empty")}</span>}
          </pre>
        </div>
      )}
    </div>
  )
}
