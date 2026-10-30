import { Crown, KeyRound, Pencil, Trash2, User as UserIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { User } from "@/features/users/types"
import { VaultAdminReset } from "@/features/vault/VaultAdminReset"
import { AdminAction, AdminStatus } from "./ui"

interface Props {
  users: User[]
  currentUsername: string
  onEdit: (user: User) => void
  onPassword: (username: string) => void
  onDelete: (username: string) => void
  onNotice: (message: string) => void
  onError: (message: string) => void
}

/** Benutzerliste des Admin-Fensters (Reiter „Benutzer“, Plan admin-reiter-benutzer). */
export function UserRows({ users, currentUsername, onEdit, onPassword, onDelete, onNotice, onError }: Props) {
  const { t } = useTranslation("users")
  return (
    <div className="space-y-2">
      {users.map((user) => {
        const isSelf = user.username === currentUsername
        const RoleIcon = user.role === "admin" ? Crown : UserIcon
        return (
          <div key={user.username} className="flex items-center gap-3 rounded-[6px] border border-s-rand bg-s-innen p-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-[4px] border border-s-rand bg-s-innen text-sm font-black text-[#69d7ff]">
              {user.username[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="truncate text-sm font-bold text-[#e8eef8]">{user.username}</p>
                {isSelf && <AdminStatus>{t("you_marker")}</AdminStatus>}
              </div>
              <p className="mt-1 flex items-center gap-1 text-xs text-[#9aa7bc]">
                <RoleIcon size={11} className="text-[#69d7ff]" />{t(`role.${user.role}`)}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <AdminAction tone="ghost" className="px-2" onClick={() => onEdit(user)} title={t("actions.edit")} aria-label={t("actions.edit")}>
                <Pencil size={14} />
              </AdminAction>
              <AdminAction tone="ghost" className="px-2" onClick={() => onPassword(user.username)} title={t("actions.change_password")} aria-label={t("actions.change_password")}>
                <KeyRound size={14} />
              </AdminAction>
              <VaultAdminReset userId={user.user_id} username={user.username} onDone={onNotice} onError={onError} />
              <AdminAction tone="danger" className="px-2" onClick={() => onDelete(user.username)} disabled={isSelf} title={t("actions.delete")} aria-label={t("actions.delete")}>
                <Trash2 size={14} />
              </AdminAction>
            </div>
          </div>
        )
      })}
    </div>
  )
}
