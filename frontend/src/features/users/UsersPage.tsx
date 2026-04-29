import { useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { ChangePasswordDialog } from "./ChangePasswordDialog"
import { NewUserDialog } from "./NewUserDialog"
import { UserList } from "./UserList"
import { usersApi } from "./api"
import type { User } from "./types"

export function UsersPage() {
  const { t } = useTranslation("users")
  const currentUsername = useAuthStore((s) => s.username) ?? ""
  const [users, setUsers] = useState<User[]>([])
  const [showNew, setShowNew] = useState(false)
  const [pwTarget, setPwTarget] = useState<string | null>(null)

  async function load() {
    try { setUsers(await usersApi.list()) } catch { /* leise */ }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(username: string) {
    if (username === currentUsername) {
      alert(t("errors.self_delete"))
      return
    }
    if (!confirm(t("actions.delete_confirm", { name: username }))) return
    try {
      await usersApi.delete(username)
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : "Error")
    }
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium shadow-md shadow-violet-900/20 transition-all"
        >
          <Plus size={14} /> {t("actions.new")}
        </button>
      </div>

      <UserList
        users={users}
        currentUsername={currentUsername}
        onChangePassword={setPwTarget}
        onDelete={handleDelete}
      />

      {showNew && (
        <NewUserDialog
          onClose={() => setShowNew(false)}
          onCreated={() => { setShowNew(false); load() }}
        />
      )}

      {pwTarget && (
        <ChangePasswordDialog
          username={pwTarget}
          onClose={() => setPwTarget(null)}
          onChanged={() => setPwTarget(null)}
        />
      )}
    </div>
  )
}
