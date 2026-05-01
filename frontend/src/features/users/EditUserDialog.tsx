import { useState } from "react"
import { X } from "lucide-react"
import { useTranslation } from "react-i18next"
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
  const [role, setRole] = useState<UserRole>(user.role)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dirty = role !== user.role

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!dirty) { onClose(); return }
    setBusy(true); setError(null)
    try {
      await usersApi.update(user.username, { role })
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{t("edit_dialog.title", { name: user.username })}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{t("fields.role")}</label>
          <select value={role} onChange={(e) => setRole(e.target.value as UserRole)} autoFocus
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
            <option value="user">{t("role.user")}</option>
            <option value="admin">{t("role.admin")}</option>
          </select>
        </div>

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            {tCommon("actions.cancel")}
          </button>
          <button type="submit" disabled={busy || !dirty}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
            {tCommon("actions.save")}
          </button>
        </div>
      </form>
    </div>
  )
}
