import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Copy, KeyRound } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { AdminAction } from "@/features/cockpit/admin/ui/AdminAction"
import { AdminField, adminInputClass } from "@/features/cockpit/admin/ui/AdminField"
import { AdminFeedback, AdminCodeBlock } from "@/features/cockpit/admin/ui/AdminFeedback"
import { nodesApi } from "./api"
import { shortDateTime } from "./format"
import type { CreatedEnrollment } from "./types"

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function EnrollNodeDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("nodes")
  const [name, setName] = useState("")
  const [ttl, setTtl] = useState(900)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<CreatedEnrollment | null>(null)
  const [copied, setCopied] = useState(false)

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const result = await nodesApi.createEnrollment({ requested_name: name.trim(), ttl_seconds: ttl })
      setCreated(result)
      onCreated()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  const copyToken = async () => {
    if (!created) return
    try {
      await navigator.clipboard.writeText(created.token)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard denied — token stays visible for manual copy */
    }
  }

  if (created) {
    return (
      <AdminDialog
        eyebrow="Admin"
        title={t("enroll.token_title")}
        icon={<KeyRound size={16} />}
        onClose={onClose}
        maxWidthClass="max-w-lg"
        footer={<AdminAction tone="primary" onClick={onClose}>{t("enroll.done")}</AdminAction>}
      >
        <div className="space-y-3">
          <AdminFeedback tone="warning">{t("enroll.token_warning")}</AdminFeedback>
          <AdminCodeBlock>{created.token}</AdminCodeBlock>
          <div className="flex items-center gap-2">
            <AdminAction onClick={copyToken}>
              <Copy size={12} className="mr-1 inline" />{copied ? t("enroll.copied") : t("enroll.copy")}
            </AdminAction>
            <span className="text-[11px] text-[#5b6675]">
              {t("enroll.expires_at")}: {shortDateTime(created.expires_at)}
            </span>
          </div>
          <p className="text-[11px] leading-relaxed text-[#8d9ab0]">{t("enroll.token_next")}</p>
        </div>
      </AdminDialog>
    )
  }

  return (
    <AdminDialog
      eyebrow="Admin"
      title={t("enroll.title")}
      icon={<KeyRound size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-lg"
      footer={
        <>
          <AdminAction onClick={onClose} disabled={busy}>{t("confirm.cancel")}</AdminAction>
          <AdminAction tone="primary" onClick={submit} disabled={busy || name.trim().length === 0}>
            {busy ? t("enroll.submitting") : t("enroll.submit")}
          </AdminAction>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-[#d4deeb]">{t("enroll.intro")}</p>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        <AdminField label={t("enroll.field_name")} help={t("enroll.field_name_hint")}>
          <input
            className={adminInputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="compute-01"
            autoFocus
            disabled={busy}
          />
        </AdminField>
        <AdminField label={t("enroll.field_ttl")} help={t("enroll.field_ttl_hint")}>
          <input
            type="number"
            min={30}
            max={3600}
            className={adminInputClass}
            value={ttl}
            onChange={(e) => setTtl(Number(e.target.value))}
            disabled={busy}
          />
        </AdminField>
      </div>
    </AdminDialog>
  )
}
