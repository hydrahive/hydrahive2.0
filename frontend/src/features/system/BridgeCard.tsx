import { useEffect, useRef, useState } from "react"
import { CheckCircle2, Network, Play, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminCodeBlock,
  AdminFeedback,
  AdminPanel,
  AdminStatus,
} from "@/features/cockpit/admin/ui"
import { systemApi } from "./api"

type Phase = "idle" | "confirm" | "running" | "done" | "failed"

export function BridgeCard() {
  const { t } = useTranslation("system")
  const { t: tCommon } = useTranslation("common")
  const [status, setStatus] = useState<{ installed: boolean; state?: string; ip?: string } | null>(null)
  const [phase, setPhase] = useState<Phase>("idle")
  const [log, setLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

  async function reload() {
    try { setStatus(await systemApi.bridgeStatus()) }
    catch { setStatus({ installed: false }) }
  }

  useEffect(() => {
    const initialLoad = setTimeout(() => { void reload() }, 0)
    return () => clearTimeout(initialLoad)
  }, [])

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
    void pull()
    const interval = phase === "running" ? setInterval(pull, 1500) : null
    return () => { alive = false; if (interval) clearInterval(interval) }
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
      await new Promise((resolve) => setTimeout(resolve, 2000))
      try {
        const nextStatus = await systemApi.bridgeStatus()
        if (nextStatus.installed) {
          setStatus(nextStatus); setPhase("done"); return
        }
      } catch { /* server can flap during netplan apply */ }
    }
    setPhase("failed"); setError(t("bridge.timeout"))
  }

  const statusBadge = status ? (
    <AdminStatus
      tone={status.installed ? "success" : "warning"}
      icon={status.installed ? CheckCircle2 : XCircle}
    >
      {status.installed ? (status.state ?? "up") : t("bridge.not_installed")}
    </AdminStatus>
  ) : undefined

  return (
    <AdminPanel
      title={t("bridge.title")}
      description={t("bridge.subtitle")}
      icon={Network}
      actions={statusBadge}
      bodyClassName="space-y-3"
    >
      {status?.installed && status.ip && (
        <p className="font-mono text-xs text-[#8d9ab0]">br0 · {status.ip}</p>
      )}

      {!status?.installed && phase === "idle" && (
        <AdminAction onClick={() => setPhase("confirm")} tone="primary">
          <Play size={11} /> {t("bridge.setup")}
        </AdminAction>
      )}

      {phase === "confirm" && (
        <div className="space-y-3">
          <AdminFeedback tone="warning">
            <p>{t("bridge.confirm_question")}</p>
            <p className="mt-1 text-[#8d9ab0]">{t("bridge.confirm_hint")}</p>
          </AdminFeedback>
          <div className="flex justify-end gap-2">
            <AdminAction onClick={() => setPhase("idle")}>{tCommon("actions.cancel")}</AdminAction>
            <AdminAction onClick={start} tone="primary">{t("bridge.confirm_button")}</AdminAction>
          </div>
        </div>
      )}

      {(phase === "running" || phase === "done" || phase === "failed") && (
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              {phase === "running" && <AdminFeedback tone="warning" loading>{t("bridge.running")}</AdminFeedback>}
              {phase === "done" && <AdminFeedback tone="success">{t("bridge.done")}</AdminFeedback>}
              {phase === "failed" && <AdminFeedback tone="danger">{error ?? t("bridge.failed")}</AdminFeedback>}
            </div>
            {(phase === "done" || phase === "failed") && (
              <AdminAction
                tone="ghost"
                className="px-2"
                aria-label={tCommon("actions.close")}
                title={tCommon("actions.close")}
                onClick={() => { setPhase("idle"); setLog([]) }}
              >
                <X size={11} />
              </AdminAction>
            )}
          </div>
          <div ref={logRef} className="max-h-[260px] min-h-[120px] overflow-auto">
            <AdminCodeBlock className="min-h-[120px]">
              {log.length > 0 ? log.join("") : t("bridge.log_empty")}
            </AdminCodeBlock>
          </div>
        </div>
      )}
    </AdminPanel>
  )
}
