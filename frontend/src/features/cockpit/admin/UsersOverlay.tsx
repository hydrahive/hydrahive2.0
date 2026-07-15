import { useEffect, useState } from "react"
import { Crown, KeyRound, Pencil, Plus, Trash2, User as UserIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { ApiKeysSection } from "@/features/users/ApiKeysSection"
import { ChangePasswordDialog } from "@/features/users/ChangePasswordDialog"
import { EditUserDialog } from "@/features/users/EditUserDialog"
import { NewUserDialog } from "@/features/users/NewUserDialog"
import { usersApi } from "@/features/users/api"
import type { User } from "@/features/users/types"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

export function UsersOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("users")
  const currentUsername = useAuthStore((s) => s.username) ?? ""
  const [users, setUsers] = useState<User[]>([])
  const [showNew, setShowNew] = useState(false)
  const [pwTarget, setPwTarget] = useState<string | null>(null)
  const [editTarget, setEditTarget] = useState<User | null>(null)

  async function load() {
    try { setUsers(await usersApi.list()) } catch { /* leise */ }
  }
  useEffect(() => { load() }, [])

  async function handleDelete(username: string) {
    if (username === currentUsername) { alert(t("errors.self_delete")); return }
    if (!confirm(t("actions.delete_confirm", { name: username }))) return
    try { await usersApi.delete(username); await load() }
    catch (e) { alert(e instanceof Error ? e.message : "Error") }
  }

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      headerActions={
        <CockpitButton tone="primary" onClick={() => setShowNew(true)}>
          <Plus size={13} className="mr-1 inline" />{t("actions.new")}
        </CockpitButton>
      }
    >
      <div className="space-y-5">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>

        <div className="space-y-2">
          {users.length === 0 ? (
            <p className="py-6 text-center text-sm text-[#8d9ab0]">{t("no_users")}</p>
          ) : (
            users.map((u) => {
              const isSelf = u.username === currentUsername
              const Icon = u.role === "admin" ? Crown : UserIcon
              return (
                <div key={u.username} className="flex items-center gap-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-700 text-sm font-bold text-white">
                    {u.username[0]?.toUpperCase() ?? "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 truncate text-sm font-medium text-[#e8eef8]">
                      {u.username}
                      {isSelf && <span className="text-[10px] font-normal text-[#8d9ab0]">{t("you_marker")}</span>}
                    </p>
                    <p className="mt-0.5 flex items-center gap-1 text-xs text-[#8d9ab0]">
                      <Icon size={11} className={u.role === "admin" ? "text-violet-400" : "text-[#8d9ab0]"} />
                      {t(`role.${u.role}`)}
                    </p>
                  </div>
                  <button onClick={() => setEditTarget(u)} title={t("actions.edit")} className="rounded-[4px] p-2 text-[#8d9ab0] transition-colors hover:bg-indigo-500/10 hover:text-indigo-300">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => setPwTarget(u.username)} title={t("actions.change_password")} className="rounded-[4px] p-2 text-[#8d9ab0] transition-colors hover:bg-violet-500/10 hover:text-violet-300">
                    <KeyRound size={14} />
                  </button>
                  <button onClick={() => handleDelete(u.username)} disabled={isSelf} title={t("actions.delete")} className="rounded-[4px] p-2 text-[#8d9ab0] transition-colors hover:bg-rose-500/10 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-30">
                    <Trash2 size={14} />
                  </button>
                </div>
              )
            })
          )}
        </div>

        <div className="border-t border-[#2a364b]" />
        <ApiKeysSection />
      </div>

      {showNew && <NewUserDialog onClose={() => setShowNew(false)} onCreated={() => { setShowNew(false); load() }} />}
      {pwTarget && <ChangePasswordDialog username={pwTarget} onClose={() => setPwTarget(null)} onChanged={() => setPwTarget(null)} />}
      {editTarget && <EditUserDialog user={editTarget} onClose={() => setEditTarget(null)} onSaved={() => { setEditTarget(null); load() }} />}
    </AdminOverlay>
  )
}
