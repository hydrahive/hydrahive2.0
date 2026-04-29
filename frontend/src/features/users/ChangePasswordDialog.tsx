import { useState } from "react"
import { X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { usersApi } from "./api"

interface Props {
  username: string
  onClose: () => void
  onChanged: () => void
}

export function ChangePasswordDialog({ username, onClose, onChanged }: Props) {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      await usersApi.changePassword(username, password)
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{t("password_dialog.title", { name: username })}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{t("password_dialog.new_password_label")}</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoFocus
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm" />
          <p className="text-[11px] text-zinc-600">{t("password_dialog.min_length_hint")}</p>
        </div>

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            {tCommon("actions.cancel")}
          </button>
          <button type="submit" disabled={busy || password.length < 8}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
            {tCommon("actions.save")}
          </button>
        </div>
      </form>
    </div>
  )
}
