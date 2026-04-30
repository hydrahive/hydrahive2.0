import { AlertTriangle, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"

export type RestoreState = "idle" | "confirm" | "uploading" | "waiting" | "done" | "failed"

export function BackupRestoreModal({ state, error, fileName, onConfirm, onClose }: {
  state: RestoreState
  error: string | null
  fileName?: string
  onConfirm: () => void
  onClose: () => void
}) {
  const { t } = useTranslation("system")
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="rounded-xl border border-white/10 bg-zinc-900 p-6 max-w-md w-full mx-4 space-y-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-white">{t("backup.restore_title")}</h2>
            {state === "confirm" && (
              <p className="text-sm text-zinc-400">{t("backup.restore_warning", { file: fileName })}</p>
            )}
            {state === "uploading" && <p className="text-sm text-zinc-400">{t("backup.uploading")}</p>}
            {state === "waiting" && <p className="text-sm text-zinc-400">{t("backup.waiting_restart")}</p>}
            {state === "done" && <p className="text-sm text-emerald-400">{t("backup.restore_done")}</p>}
            {state === "failed" && <p className="text-sm text-red-400">{error || t("backup.restore_failed")}</p>}
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          {state === "confirm" && (
            <>
              <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                {t("backup.cancel")}
              </button>
              <button onClick={onConfirm} className="px-3 py-1.5 rounded-lg bg-amber-600 text-white text-xs font-medium hover:bg-amber-500 transition-colors">
                {t("backup.confirm_restore")}
              </button>
            </>
          )}
          {(state === "uploading" || state === "waiting") && (
            <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
          )}
          {(state === "done" || state === "failed") && (
            <button onClick={onClose} className="px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%] transition-colors">
              {t("backup.close")}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
