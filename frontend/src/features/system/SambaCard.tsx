import { useEffect, useRef, useState } from "react"
import { CheckCircle2, Copy, Eye, EyeOff, FolderOpen, Play, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminCodeBlock,
  AdminFeedback,
  AdminPanel,
  AdminStatus,
} from "@/features/cockpit/admin/ui"
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
  const logRef = useRef<HTMLDivElement>(null)

  async function reload() {
    try { setStatus(await systemApi.sambaStatus()) }
    catch { /* leise */ }
  }

  useEffect(() => {
    const initialLoad = setTimeout(() => { void reload() }, 0)
    return () => clearTimeout(initialLoad)
  }, [])

  useEffect(() => {
    if (phase !== "running") return
    let alive = true
    async function pull() {
      try {
        const response = await systemApi.sambaLog(200)
        if (!alive) return
        if (response.exists) setLog(response.lines)
      } catch { /* ignore */ }
    }
    void pull()
    const interval = setInterval(pull, 1500)
    return () => { alive = false; clearInterval(interval) }
  }, [phase])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  async function start() {
    setPhase("running"); setError(null); setLog([])
    try { await systemApi.sambaSetup() }
    catch (e) { setPhase("failed"); setError(e instanceof Error ? e.message : ""); return }
    const startedAt = Date.now()
    while (Date.now() - startedAt < 300_000) {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      try {
        const nextStatus = await systemApi.sambaStatus()
        if (nextStatus.installed && nextStatus.running) {
          setStatus(nextStatus); setPhase("done"); return
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

  const isRunning = Boolean(status?.installed && status.running)

  return (
    <AdminPanel
      title={t("samba.title")}
      description={t("samba.subtitle")}
      icon={FolderOpen}
      actions={status ? (
        <AdminStatus tone={isRunning ? "success" : "warning"} icon={isRunning ? CheckCircle2 : XCircle}>
          {isRunning ? t("samba.running") : t("samba.not_installed")}
        </AdminStatus>
      ) : undefined}
      bodyClassName="space-y-3"
    >
      {status?.installed && status.password_set && (
        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-xs">
          <span className="text-[#8d9ab0]">{t("samba.user")}</span>
          <span className="font-mono text-[#e8eef8]">{status.user}</span>
          <span className="text-[#8d9ab0]">{t("samba.password")}</span>
          <span className="flex min-w-0 items-center gap-1.5">
            <span className="min-w-0 flex-1 truncate font-mono text-[#e8eef8]">
              {showPwd ? status.password : "••••••••••••"}
            </span>
            <AdminAction
              tone="ghost"
              className="px-2"
              onClick={() => setShowPwd(!showPwd)}
              aria-label={t("samba.password")}
              title={t("samba.password")}
            >
              {showPwd ? <EyeOff size={11} /> : <Eye size={11} />}
            </AdminAction>
            <AdminAction
              tone="ghost"
              className="px-2"
              onClick={copyPassword}
              aria-label={copied ? t("samba.copied") : t("samba.copy")}
              title={copied ? t("samba.copied") : t("samba.copy")}
            >
              {copied ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
            </AdminAction>
          </span>
        </div>
      )}

      {!status?.installed && phase === "idle" && (
        <AdminAction onClick={start} tone="primary">
          <Play size={11} /> {t("samba.setup")}
        </AdminAction>
      )}

      {(phase === "running" || phase === "done" || phase === "failed") && (
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              {phase === "running" && <AdminFeedback tone="warning" loading>{t("samba.running_setup")}</AdminFeedback>}
              {phase === "done" && <AdminFeedback tone="success">{t("samba.done")}</AdminFeedback>}
              {phase === "failed" && <AdminFeedback tone="danger">{error ?? t("samba.failed")}</AdminFeedback>}
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
              {log.length > 0 ? log.join("") : tCommon("status.empty")}
            </AdminCodeBlock>
          </div>
        </div>
      )}
    </AdminPanel>
  )
}
