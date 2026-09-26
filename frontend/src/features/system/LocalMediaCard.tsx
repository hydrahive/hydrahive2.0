import { useEffect, useRef } from "react"
import { CheckCircle2, Download, ImagePlay, Lock, Trash2, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminCodeBlock, AdminFeedback, AdminPanel, AdminStatus } from "@/features/cockpit/admin/ui"
import { gib } from "./localMediaApi"
import { useLocalMedia } from "./useLocalMedia"

export function LocalMediaCard() {
  const { t } = useTranslation("system")
  const { t: tCommon } = useTranslation("common")
  const lm = useLocalMedia()
  const logRef = useRef<HTMLDivElement>(null)
  const s = lm.status

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [lm.log])

  const badge = s ? (
    <AdminStatus tone={s.installed ? "success" : "neutral"} icon={s.installed ? CheckCircle2 : XCircle}>
      {s.installed ? t("local_media.installed") : t("local_media.not_installed")}
    </AdminStatus>
  ) : undefined

  const gpuLine = s?.gpu
    ? t("local_media.gpu", { name: s.gpu.name, vram: (s.gpu.vram_mib / 1024).toFixed(1) })
    : t("local_media.gpu_none")
  const blocked = s && !s.installed && s.blocked_reason
  const busy = lm.phase !== "idle" && lm.phase !== "confirm"
  const verb = lm.action === "install" ? "install" : "uninstall"

  return (
    <AdminPanel title={t("local_media.title")} description={t("local_media.subtitle")} icon={ImagePlay}
      actions={badge} bodyClassName="space-y-3">
      {s && <p className="font-mono text-xs text-[#8d9ab0]">{gpuLine}</p>}

      {blocked && (
        <AdminFeedback tone="warning">
          <Lock size={11} className="mr-1 inline" />
          {t(`local_media.blocked.${s.blocked_reason}`, {
            min: (s.min_vram_mib / 1024).toFixed(0), free: gib(s.free_bytes), need: gib(s.min_free_bytes),
          })}
        </AdminFeedback>
      )}

      {s && lm.phase === "idle" && (s.installed ? (
        <AdminAction onClick={() => lm.ask("uninstall")} tone="danger" disabled={!s.can_uninstall}>
          <Trash2 size={11} /> {t("local_media.uninstall")}
        </AdminAction>
      ) : (
        <AdminAction onClick={() => lm.ask("install")} tone="primary" disabled={!s.can_install}
          title={blocked ? t("local_media.blocked_title") : undefined}>
          <Download size={11} /> {t("local_media.install", { size: gib(s.download_bytes) })}
        </AdminAction>
      ))}

      {lm.phase === "confirm" && s && (
        <div className="space-y-3">
          <AdminFeedback tone="warning">
            <p>{t(`local_media.confirm_${verb}`, { size: gib(s.download_bytes), free: gib(s.free_bytes) })}</p>
            <p className="mt-1 text-[#8d9ab0]">{t(`local_media.confirm_${verb}_hint`, { size: gib(s.download_bytes) })}</p>
          </AdminFeedback>
          <div className="flex justify-end gap-2">
            <AdminAction onClick={lm.close}>{tCommon("actions.cancel")}</AdminAction>
            <AdminAction onClick={lm.confirm} tone={lm.action === "install" ? "primary" : "danger"}>
              {t(`local_media.confirm_${verb}_button`)}
            </AdminAction>
          </div>
        </div>
      )}

      {busy && (
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              {lm.phase === "running" && <AdminFeedback tone="warning" loading>{t(`local_media.running_${verb}`)}</AdminFeedback>}
              {lm.phase === "done" && <AdminFeedback tone="success">{t(`local_media.done_${verb}`)}</AdminFeedback>}
              {lm.phase === "failed" && <AdminFeedback tone="danger">{lm.error ?? t("local_media.failed")}</AdminFeedback>}
            </div>
            {lm.phase !== "running" && (
              <AdminAction tone="ghost" className="px-2" aria-label={tCommon("actions.close")}
                title={tCommon("actions.close")} onClick={lm.close}>
                <X size={11} />
              </AdminAction>
            )}
          </div>
          <div ref={logRef} className="max-h-[260px] min-h-[120px] overflow-auto">
            <AdminCodeBlock className="min-h-[120px]">
              {lm.log.length > 0 ? lm.log.join("") : t("local_media.log_empty")}
            </AdminCodeBlock>
          </div>
        </div>
      )}
    </AdminPanel>
  )
}
