import { AlertTriangle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback } from "@/features/cockpit/admin/ui"

export type RestoreState = "idle" | "confirm" | "uploading" | "waiting" | "done" | "failed"

export function BackupRestoreModal({ state, error, fileName, onConfirm, onClose }: {
  state: RestoreState
  error: string | null
  fileName?: string
  onConfirm: () => void
  onClose: () => void
}) {
  const { t } = useTranslation("system")
  const dismissable = state === "confirm" || state === "done" || state === "failed"
  const footer = state === "confirm" ? (
    <>
      <AdminAction onClick={onClose}>{t("backup.cancel")}</AdminAction>
      <AdminAction onClick={onConfirm} tone="danger">{t("backup.confirm_restore")}</AdminAction>
    </>
  ) : (state === "done" || state === "failed") ? (
    <AdminAction onClick={onClose} tone="primary">{t("backup.close")}</AdminAction>
  ) : undefined

  return (
    <AdminDialog
      eyebrow="System · Backup"
      title={t("backup.restore_title")}
      icon={<AlertTriangle size={16} />}
      onClose={dismissable ? onClose : undefined}
      footer={footer}
      maxWidthClass="max-w-md"
    >
      {state === "confirm" && (
        <AdminFeedback tone="warning">{t("backup.restore_warning", { file: fileName })}</AdminFeedback>
      )}
      {state === "uploading" && <AdminFeedback tone="warning" loading>{t("backup.uploading")}</AdminFeedback>}
      {state === "waiting" && <AdminFeedback tone="warning" loading>{t("backup.waiting_restart")}</AdminFeedback>}
      {state === "done" && <AdminFeedback tone="success">{t("backup.restore_done")}</AdminFeedback>}
      {state === "failed" && <AdminFeedback tone="danger">{error || t("backup.restore_failed")}</AdminFeedback>}
    </AdminDialog>
  )
}
