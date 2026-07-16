import { useId, useState } from "react"
import { Pencil } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback, AdminField, adminInputClass } from "@/features/cockpit/admin/ui"
import { usersApi } from "./api"
import type { User, UserRole } from "./types"

interface Props {
  user: User
  onClose: () => void
  onSaved: () => void
}

export function EditUserDialog({ user, onClose, onSaved }: Props) {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const formId = useId()
  const [role, setRole] = useState<UserRole>(user.role)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dirty = role !== user.role

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!dirty) { onClose(); return }
    setBusy(true)
    setError(null)
    try {
      await usersApi.update(user.username, { role })
      onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin · Benutzer"
      title={t("edit_dialog.title", { name: user.username })}
      icon={<Pencil size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-md"
      footer={(
        <>
          <AdminAction onClick={onClose} disabled={busy}>{tCommon("actions.cancel")}</AdminAction>
          <AdminAction type="submit" form={formId} tone="primary" disabled={busy || !dirty}>{tCommon("actions.save")}</AdminAction>
        </>
      )}
    >
      <form id={formId} onSubmit={submit} className="space-y-4">
        <AdminField label={t("fields.role")}>
          <select value={role} onChange={(event) => setRole(event.target.value as UserRole)} autoFocus className={adminInputClass}>
            <option value="user">{t("role.user")}</option>
            <option value="admin">{t("role.admin")}</option>
          </select>
        </AdminField>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      </form>
    </AdminDialog>
  )
}
