import { useState } from "react"
import { useTranslation } from "react-i18next"
import { ShieldCheck } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { AdminAction } from "@/features/cockpit/admin/ui/AdminAction"
import { AdminField, adminInputClass } from "@/features/cockpit/admin/ui/AdminField"
import { AdminFeedback, AdminCodeBlock } from "@/features/cockpit/admin/ui/AdminFeedback"
import { nodesApi } from "./api"
import type { ComputeNode } from "./types"

interface Props {
  node: ComputeNode
  onClose: () => void
  onApproved: () => void
}

export function ApproveNodeDialog({ node, onClose, onApproved }: Props) {
  const { t } = useTranslation("nodes")
  const [fingerprint, setFingerprint] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      await nodesApi.approve(node.node_id, { certificate_fingerprint: fingerprint.trim() })
      onApproved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin"
      title={t("approve.title")}
      icon={<ShieldCheck size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-lg"
      footer={
        <>
          <AdminAction onClick={onClose} disabled={busy}>{t("confirm.cancel")}</AdminAction>
          <AdminAction tone="primary" onClick={submit} disabled={busy || fingerprint.trim().length < 64}>
            {busy ? t("approve.submitting") : t("approve.submit")}
          </AdminAction>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-[#d4deeb]">{t("approve.intro")}</p>
        {node.certificate_fingerprint && (
          <div className="space-y-1">
            <span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">{t("approve.reported_fingerprint")}</span>
            <AdminCodeBlock>{node.certificate_fingerprint}</AdminCodeBlock>
          </div>
        )}
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        <AdminField label={t("approve.field_fingerprint")} help={t("approve.field_fingerprint_hint")}>
          <input
            className={adminInputClass}
            value={fingerprint}
            onChange={(e) => setFingerprint(e.target.value)}
            placeholder="sha256:…"
            autoFocus
            disabled={busy}
          />
        </AdminField>
      </div>
    </AdminDialog>
  )
}
