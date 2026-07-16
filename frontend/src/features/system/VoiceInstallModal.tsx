import { useEffect, useRef, useState } from "react"
import { Mic } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminCodeBlock, AdminDialog, AdminFeedback } from "@/features/cockpit/admin/ui"
import { systemApi } from "./api"

export type VoiceInstallState = "confirm" | "starting" | "running" | "done" | "failed"

interface Props {
  state: VoiceInstallState
  errorMessage?: string | null
  onConfirm: () => void
  onClose: () => void
}

export function VoiceInstallModal({ state, errorMessage, onConfirm, onClose }: Props) {
  const { t } = useTranslation("system")
  const [logLines, setLogLines] = useState<string[]>([])
  const logRef = useRef<HTMLDivElement>(null)
  const isPolling = state === "starting" || state === "running"
  const dismissable = state === "confirm" || state === "done" || state === "failed"

  useEffect(() => {
    if (!isPolling && state !== "done" && state !== "failed") return
    let alive = true
    async function fetchLog() {
      try {
        const response = await systemApi.voiceLog(300)
        if (alive && response.exists) setLogLines(response.lines)
      } catch { /* Die Installation läuft unabhängig vom optionalen Log-Polling. */ }
    }
    fetchLog()
    const interval = isPolling ? setInterval(fetchLog, 1500) : null
    return () => { alive = false; if (interval) clearInterval(interval) }
  }, [state, isPolling])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logLines])

  const footer = state === "confirm" ? (
    <>
      <AdminAction onClick={onClose}>{t("voice_install.cancel")}</AdminAction>
      <AdminAction tone="primary" onClick={onConfirm}>{t("voice_install.install")}</AdminAction>
    </>
  ) : dismissable ? (
    <AdminAction tone="primary" onClick={onClose}>Schließen</AdminAction>
  ) : undefined

  return (
    <AdminDialog
      eyebrow="System · Voice"
      title={t("voice_install.title")}
      icon={<Mic size={16} />}
      onClose={dismissable ? onClose : undefined}
      footer={footer}
    >
      <div className="space-y-4">
        {state === "confirm" && (
          <>
            <p className="text-sm text-[#e8eef8]">Wyoming STT (faster-whisper) und TTS (Piper) als Incus-Container installieren?</p>
            <ul className="list-inside list-disc space-y-1 text-xs leading-relaxed text-[#8d9ab0]">
              <li>{t("voice_install.lxc_hint")}</li>
              <li>{t("voice_install.download_hint")}</li>
              <li>{t("voice_install.ports_hint")}</li>
              <li>{t("voice_install.autostart_hint")}</li>
            </ul>
          </>
        )}

        {state === "starting" && <AdminFeedback tone="warning" loading>{t("voice_install.starting")}</AdminFeedback>}
        {state === "running" && <AdminFeedback tone="warning" loading>{t("voice_install.running")}</AdminFeedback>}
        {state === "done" && <AdminFeedback tone="success">{t("voice_install.done_msg")}</AdminFeedback>}
        {state === "failed" && <AdminFeedback tone="danger">{t("voice_install.failed")}: {errorMessage ?? t("voice_install.unknown_error")}</AdminFeedback>}

        {state !== "confirm" && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#8d9ab0]">{t("voice_install.log_title")}</p>
            <div ref={logRef} className="max-h-[400px] min-h-[240px] overflow-auto">
              <AdminCodeBlock className="min-h-[240px]">
                {logLines.length > 0 ? logLines.join("") : t("voice_install.log_empty")}
              </AdminCodeBlock>
            </div>
          </div>
        )}
      </div>
    </AdminDialog>
  )
}
