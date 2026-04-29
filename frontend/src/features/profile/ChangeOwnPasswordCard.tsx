import { useState } from "react"
import { CheckCircle, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { profileApi } from "./api"

export function ChangeOwnPasswordCard() {
  const { t } = useTranslation("profile")
  const { t: tCommon } = useTranslation("common")
  const [pw, setPw] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null); setSuccess(false)
    try {
      await profileApi.changeOwnPassword(pw)
      setPw("")
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-white/[8%] bg-white/[2%] p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">{t("password.title")}</h2>
        <p className="text-xs text-zinc-500 mt-0.5">{t("password.description")}</p>
      </div>
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">{t("password.new_label")}</label>
        <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} required minLength={8}
          className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm" />
        <p className="text-[11px] text-zinc-600">{t("password.min_length_hint")}</p>
      </div>
      {error && (
        <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
      )}
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy || pw.length < 8}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
          {busy && <Loader2 size={13} className="animate-spin" />}
          {t("password.button")}
        </button>
        {success && (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <CheckCircle size={13} /> {t("password.success")}
          </span>
        )}
      </div>
    </form>
  )
}
