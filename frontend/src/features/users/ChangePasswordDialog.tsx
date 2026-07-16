import { useId, useState } from "react"
import { KeyRound } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback, AdminField, adminInputClass } from "@/features/cockpit/admin/ui"
import { usersApi } from "./api"

interface Props {
  username: string
  onClose: () => void
  onChanged: () => void
}

export function ChangePasswordDialog({ username, onClose, onChanged }: Props) {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const formId = useId()
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await usersApi.changePassword(username, password)
      setPassword("")
      onChanged()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin · Benutzer"
      title={t("password_dialog.title", { name: username })}
      icon={<KeyRound size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-md"
      footer={(
        <>
          <AdminAction onClick={onClose} disabled={busy}>{tCommon("actions.cancel")}</AdminAction>
          <AdminAction type="submit" form={formId} tone="primary" disabled={busy || password.length < 8}>{tCommon("actions.save")}</AdminAction>
        </>
      )}
    >
      <form id={formId} onSubmit={submit} className="space-y-4">
        <AdminField label={t("password_dialog.new_password_label")} help={t("password_dialog.min_length_hint")}>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8}
            autoFocus autoComplete="new-password" className={adminInputClass} />
        </AdminField>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      </form>
    </AdminDialog>
  )
}
