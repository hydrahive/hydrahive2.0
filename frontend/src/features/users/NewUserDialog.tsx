import { useId, useState } from "react"
import { UserPlus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback, AdminField, adminInputClass } from "@/features/cockpit/admin/ui"
import { usersApi } from "./api"
import type { UserRole } from "./types"

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function NewUserDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const formId = useId()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<UserRole>("user")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await usersApi.create(username.trim(), password, role)
      setPassword("")
      onCreated()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin · Benutzer"
      title={t("new_dialog.title")}
      icon={<UserPlus size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-md"
      footer={(
        <>
          <AdminAction onClick={onClose} disabled={busy}>{tCommon("actions.cancel")}</AdminAction>
          <AdminAction type="submit" form={formId} tone="primary" disabled={busy || !username.trim() || password.length < 8}>
            {tCommon("actions.create")}
          </AdminAction>
        </>
      )}
    >
      <form id={formId} onSubmit={submit} className="space-y-4">
        <AdminField label={t("fields.username")}>
          <input value={username} onChange={(event) => setUsername(event.target.value)} required pattern="[a-zA-Z0-9_\-]+"
            placeholder={t("new_dialog.username_placeholder")} className={`${adminInputClass} font-mono`} autoFocus />
        </AdminField>
        <AdminField label={t("fields.password")} help={t("password_dialog.min_length_hint")}>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8}
            autoComplete="new-password" className={adminInputClass} />
        </AdminField>
        <AdminField label={t("fields.role")}>
          <select value={role} onChange={(event) => setRole(event.target.value as UserRole)} className={adminInputClass}>
            <option value="user">{t("role.user")}</option>
            <option value="admin">{t("role.admin")}</option>
          </select>
        </AdminField>
        {error && <AdminFeedback tone="danger"><span className="whitespace-pre-line">{error}</span></AdminFeedback>}
      </form>
    </AdminDialog>
  )
}
