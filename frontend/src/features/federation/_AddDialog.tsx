import { useState } from "react"
import { useTranslation } from "react-i18next"
import { federationApi } from "./api"

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function AddWorkstationDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("federation")
  const [name, setName] = useState("")
  const [url, setUrl] = useState("")
  const [token, setToken] = useState("")
  // verify_tls defaults to TRUE in the backend; we mirror that here.
  // The most common reason to flip it OFF is a self-signed cert
  // (ProjektX --tls-auto, Tailnet IPs, etc.). We show a hint
  // explaining when it's safe to disable.
  const [verifyTls, setVerifyTls] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !url.trim()) return
    setSaving(true); setError(null)
    try {
      await federationApi.create(name.trim(), url.trim(), token.trim(), {
        verify_tls: verifyTls,
      })
      onCreated()
    } catch (err: any) {
      setError(err?.message ?? t("add_dialog.error"))
    } finally {
      setSaving(false)
    }
  }

  const input = "w-full bg-zinc-800/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"

  // Show a contextual hint when the URL looks self-signed-ish
  // (Tailscale CGNAT 100.64.0.0/10 or .local). Pure UX — doesn't
  // change behaviour, just nudges the user to flip the toggle.
  const looksSelfSigned =
    /^https:\/\/100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./.test(url) ||
    /\.local(:|\/|$)/.test(url) ||
    /\.tailnet(:|\/|$)/.test(url)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="px-5 py-4 border-b border-white/8">
          <h2 className="text-sm font-semibold text-zinc-100">{t("add_dialog.title")}</h2>
          <p className="text-xs text-zinc-500 mt-0.5">{t("add_dialog.subtitle")}</p>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">{t("add_dialog.name_label")}</label>
            <input
              className={input}
              placeholder="projektx-till"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
            <p className="text-[10px] text-zinc-600 mt-1">
              Wird als @-Adresse genutzt: <code className="text-violet-400">geralt@{name || "name"}</code>
            </p>
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">{t("add_dialog.url_label")}</label>
            <input
              className={input}
              placeholder="https://100.127.195.68:8100"
              value={url}
              onChange={e => setUrl(e.target.value)}
              required
            />
            <p className="text-[10px] text-zinc-600 mt-1">
              Vollständige URL inkl. Port. ProjektX default: <code>:8100</code> (mit
              <code> --tls-auto</code> serviert das HTTPS mit self-signed cert).
            </p>
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">{t("add_dialog.token_label")}</label>
            <input
              className={input}
              type="password"
              placeholder={t("add_dialog.token_placeholder")}
              value={token}
              onChange={e => setToken(e.target.value)}
            />
          </div>
          <div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={verifyTls}
                onChange={e => setVerifyTls(e.target.checked)}
                className="w-4 h-4 accent-violet-500"
              />
              <span className="text-xs text-zinc-300">{t("add_dialog.tls_label")}</span>
            </label>
            <p className="text-[10px] text-zinc-600 mt-1 ml-6">
              {t("add_dialog.tls_hint")}
              {looksSelfSigned && verifyTls && (
                <span className="text-amber-400 block mt-1">{t("add_dialog.tls_warn")}</span>
              )}
            </p>
          </div>
          {error && <p className="text-xs text-rose-400">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving || !name.trim() || !url.trim()}
              className="flex-1 py-2 rounded-lg text-sm font-medium bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors"
            >
              {saving ? t("add_dialog.saving") : t("add_dialog.save")}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
            >
              {t("add_dialog.cancel")}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
