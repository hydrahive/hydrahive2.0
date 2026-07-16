import { useCallback, useEffect, useState } from "react"
import { Crown, KeyRound, Pencil, Plus, Trash2, User as UserIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { HelpButton } from "@/i18n/HelpButton"
import { ApiKeysSection } from "@/features/users/ApiKeysSection"
import { ChangePasswordDialog } from "@/features/users/ChangePasswordDialog"
import { EditUserDialog } from "@/features/users/EditUserDialog"
import { NewUserDialog } from "@/features/users/NewUserDialog"
import { usersApi } from "@/features/users/api"
import type { User } from "@/features/users/types"
import { CockpitButton } from "../CockpitButton"
import { AdminAction, AdminConfirmDialog, AdminFeedback, AdminStatus } from "./ui"
import { AdminOverlay } from "./AdminOverlay"

export function UsersOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const currentUsername = useAuthStore((state) => state.username) ?? ""
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [actionError, setActionError] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [passwordTarget, setPasswordTarget] = useState<string | null>(null)
  const [editTarget, setEditTarget] = useState<User | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    try {
      setUsers(await usersApi.list())
      setActionError(null)
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setLoading(false)
    }
  }, [tCommon])

  useEffect(() => {
    const initial = window.setTimeout(load, 0)
    return () => window.clearTimeout(initial)
  }, [load])

  async function handleDelete() {
    if (!deleteTarget || deleteTarget === currentUsername) return
    setDeleting(true)
    setActionError(null)
    try {
      await usersApi.delete(deleteTarget)
      setDeleteTarget(null)
      await load()
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : tCommon("status.error"))
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      headerActions={(
        <div className="flex items-center gap-2">
          <HelpButton topic="users" />
          <CockpitButton tone="primary" onClick={() => setShowNew(true)}>
            <Plus size={13} className="mr-1 inline" />{t("actions.new")}
          </CockpitButton>
        </div>
      )}
    >
      <div className="space-y-5">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>
        {actionError && <AdminFeedback tone="danger">{actionError}</AdminFeedback>}
        {loading && <AdminFeedback loading>Benutzer werden geladen …</AdminFeedback>}

        {!loading && !actionError && users.length === 0 ? (
          <AdminFeedback>{t("no_users")}</AdminFeedback>
        ) : (
          <div className="space-y-2">
            {users.map((user) => {
              const isSelf = user.username === currentUsername
              const RoleIcon = user.role === "admin" ? Crown : UserIcon
              return (
                <div key={user.username} className="flex items-center gap-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-3">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-[4px] border border-[#2a364b] bg-[#172133] text-sm font-black text-[#69d7ff]">
                    {user.username[0]?.toUpperCase() ?? "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-bold text-[#e8eef8]">{user.username}</p>
                      {isSelf && <AdminStatus>{t("you_marker")}</AdminStatus>}
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-xs text-[#8d9ab0]">
                      <RoleIcon size={11} className="text-[#69d7ff]" />{t(`role.${user.role}`)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <AdminAction tone="ghost" className="px-2" onClick={() => setEditTarget(user)} title={t("actions.edit")} aria-label={t("actions.edit")}>
                      <Pencil size={14} />
                    </AdminAction>
                    <AdminAction tone="ghost" className="px-2" onClick={() => setPasswordTarget(user.username)} title={t("actions.change_password")} aria-label={t("actions.change_password")}>
                      <KeyRound size={14} />
                    </AdminAction>
                    <AdminAction tone="danger" className="px-2" onClick={() => setDeleteTarget(user.username)} disabled={isSelf} title={t("actions.delete")} aria-label={t("actions.delete")}>
                      <Trash2 size={14} />
                    </AdminAction>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <ApiKeysSection />
      </div>

      {showNew && <NewUserDialog onClose={() => setShowNew(false)} onCreated={() => { setShowNew(false); load() }} />}
      {passwordTarget && <ChangePasswordDialog username={passwordTarget} onClose={() => setPasswordTarget(null)} onChanged={() => setPasswordTarget(null)} />}
      {editTarget && <EditUserDialog user={editTarget} onClose={() => setEditTarget(null)} onSaved={() => { setEditTarget(null); load() }} />}
      {deleteTarget && (
        <AdminConfirmDialog
          title={t("actions.delete")}
          confirmLabel={t("actions.delete")}
          cancelLabel={tCommon("actions.cancel")}
          onConfirm={handleDelete}
          onClose={() => setDeleteTarget(null)}
          busy={deleting}
        >
          {t("actions.delete_confirm", { name: deleteTarget })}
        </AdminConfirmDialog>
      )}
    </AdminOverlay>
  )
}
