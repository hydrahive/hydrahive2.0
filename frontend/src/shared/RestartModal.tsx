import { RotateCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback } from "@/features/cockpit/admin/ui"

export type RestartState = "confirm" | "starting" | "running" | "done" | "failed"

interface Props {
  state: RestartState
  errorMessage?: string | null
  onConfirm: () => void
  onClose: () => void
}

export function RestartModal({ state, errorMessage, onConfirm, onClose }: Props) {
  const { t } = useTranslation("nav")
  const dismissable = state === "confirm" || state === "done" || state === "failed"
  const footer = state === "confirm" ? (
    <>
      <AdminAction onClick={onClose}>{t("restart.close")}</AdminAction>
      <AdminAction tone="danger" onClick={onConfirm}>{t("restart.confirm_button")}</AdminAction>
    </>
  ) : dismissable ? (
    <AdminAction tone="primary" onClick={onClose}>{t("restart.close")}</AdminAction>
  ) : undefined

  return (
    <AdminDialog
      eyebrow="System"
      title={t("restart.modal_title")}
      icon={<RotateCw size={16} />}
      onClose={dismissable ? onClose : undefined}
      footer={footer}
      maxWidthClass="max-w-md"
    >
      <div className="space-y-3">
        {state === "confirm" && (
          <>
            <p className="text-sm text-[#e8eef8]">{t("restart.confirm_question")}</p>
            <p className="text-xs leading-relaxed text-[#8d9ab0]">{t("restart.confirm_hint")}</p>
          </>
        )}
        {state === "starting" && <AdminFeedback tone="warning" loading>{t("restart.starting")}</AdminFeedback>}
        {state === "running" && <AdminFeedback tone="warning" loading>{t("restart.in_progress")}</AdminFeedback>}
        {state === "done" && <AdminFeedback tone="success">{t("restart.done")}</AdminFeedback>}
        {state === "failed" && <AdminFeedback tone="danger">{t("restart.failed", { error: errorMessage ?? "" })}</AdminFeedback>}
      </div>
    </AdminDialog>
  )
}
