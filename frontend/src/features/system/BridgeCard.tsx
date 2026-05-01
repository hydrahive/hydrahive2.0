import { useEffect, useRef, useState } from "react"
import { CheckCircle2, Loader2, Network, Play, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { systemApi } from "./api"

type Phase = "idle" | "confirm" | "running" | "done" | "failed"

export function BridgeCard() {
  const { t } = useTranslation("system")
  const { t: tCommon } = useTranslation("common")
  const [status, setStatus] = useState<{ installed: boolean; state?: string; ip?: string } | null>(null)
  const [phase, setPhase] = useState<Phase>("idle")
  const [log, setLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLPreElement>(null)

  async function reload() {
    try { setStatus(await systemApi.bridgeStatus()) }
    catch { setStatus({ installed: false }) }
  }

  useEffect(() => { reload() }, [])

  useEffect(() => {
    if (phase !== "running" && phase !== "done") return
    let alive = true
    async function pull() {
      try {
        const r = await systemApi.bridgeLog(200)
        if (!alive) return
        if (r.exists) setLog(r.lines)
      } catch { /* ignore */ }
    }
    pull()
    const t = phase === "running" ? setInterval(pull, 1500) : null
    return () => { alive = false; if (t) clearInterval(t) }
  }, [phase])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  async function start() {
    setPhase("running"); setError(null); setLog([])
    try {
      await systemApi.bridgeSetup()
    } catch (e) {
      setPhase("failed"); setError(e instanceof Error ? e.message : ""); return
    }
    const startedAt = Date.now()
    while (Date.now() - startedAt < 180_000) {
      await new Promise((r) => setTimeout(r, 2000))
      try {
        const s = await systemApi.bridgeStatus()
        if (s.installed) {
          setStatus(s); setPhase("done"); return
        }
      } catch { /* server can flap during netplan apply */ }
    }
    setPhase("failed"); setError(t("bridge.timeout"))
  }

  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Network size={16} className="text-teal-300 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-zinc-200">{t("bridge.title")}</p>
          <p className="text-[11px] text-zinc-500 mt-0.5">{t("bridge.subtitle")}</p>
        </div>
        {status && (
          status.installed ? (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/[8%] border border-emerald-500/20 text-[10px] text-emerald-300">
              <CheckCircle2 size={10} /> {status.state ?? "up"}
            </span>
          ) : (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/[8%] border border-amber-500/20 text-[10px] text-amber-300">
              <XCircle size={10} /> {t("bridge.not_installed")}
            </span>
          )
        )}
      </div>

      {status?.installed && status.ip && (
        <p className="text-xs text-zinc-500 font-mono">br0 · {status.ip}</p>
      )}

      {!status?.installed && phase === "idle" && (
        <button onClick={() => setPhase("confirm")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white text-xs font-medium">
          <Play size={11} /> {t("bridge.setup")}
        </button>
      )}

      {phase === "confirm" && (
        <div className="rounded-md border border-amber-500/20 bg-amber-500/[6%] p-3 space-y-2">
          <p className="text-xs text-amber-200">{t("bridge.confirm_question")}</p>
          <p className="text-[11px] text-zinc-400 leading-relaxed">{t("bridge.confirm_hint")}</p>
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => setPhase("idle")}
              className="px-3 py-1 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
              {tCommon("actions.cancel")}
            </button>
            <button onClick={start}
              className="px-3 py-1 rounded-md bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium">
              {t("bridge.confirm_button")}
            </button>
          </div>
        </div>
      )}

      {(phase === "running" || phase === "done" || phase === "failed") && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            {phase === "running" && (
              <><Loader2 size={12} className="animate-spin text-amber-300" /><span className="text-amber-300">{t("bridge.running")}</span></>
            )}
            {phase === "done" && (
              <><CheckCircle2 size={12} className="text-emerald-400" /><span className="text-emerald-300">{t("bridge.done")}</span></>
            )}
            {phase === "failed" && (
              <><XCircle size={12} className="text-rose-400" /><span className="text-rose-300">{error ?? t("bridge.failed")}</span></>
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
            {log.length > 0 ? log.join("") : <span className="text-zinc-600">{t("bridge.log_empty")}</span>}
          </pre>
        </div>
      )}
    </div>
  )
}
