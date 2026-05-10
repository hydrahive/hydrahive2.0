import { Check, ClipboardCopy, KeyRound, Settings2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

interface AdminConfig {
  configured: boolean
  tailnet: string
}

interface InviteResult {
  auth_key: string
  expires: string
  id: string
}

export function TailscaleInviteSection() {
  const { t } = useTranslation("system")
  const [cfg, setCfg] = useState<AdminConfig | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [apiKey, setApiKey] = useState("")
  const [tailnet, setTailnet] = useState("-")
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [invite, setInvite] = useState<InviteResult | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadConfig() {
    try {
      const c = await api.get<AdminConfig>("/tailscale/admin-config")
      setCfg(c)
      setTailnet(c.tailnet || "-")
    } catch { /* leise */ }
  }

  useEffect(() => { loadConfig() }, [])

  async function handleSave() {
    setSaving(true); setError(null)
    try {
      const c = await api.put<AdminConfig>("/tailscale/admin-config", {
        api_key: apiKey, tailnet: tailnet || "-",
      })
      setCfg(c); setApiKey(""); setShowSettings(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.admin_save_failed"))
    } finally { setSaving(false) }
  }

  async function handleGenerate() {
    setGenerating(true); setError(null); setInvite(null)
    try {
      const r = await api.post<InviteResult>("/tailscale/invite", {})
      setInvite(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.invite_failed"))
    } finally { setGenerating(false) }
  }

  function handleCopy() {
    if (!invite?.auth_key) return
    navigator.clipboard.writeText(invite.auth_key)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  if (!cfg) return null

  return (
    <div className="pt-3 border-t border-white/[6%] space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-[10.5px] uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
          <KeyRound size={11} /> {t("tailscale.invite_title")}
        </p>
        <button onClick={() => setShowSettings(s => !s)}
          className="flex items-center gap-1 text-[10.5px] text-zinc-500 hover:text-zinc-300 transition-colors">
          <Settings2 size={10} />
          {cfg.configured ? t("tailscale.admin_configured") : t("tailscale.admin_not_configured")}
        </button>
      </div>

      <p className="text-[11px] text-zinc-500">{t("tailscale.invite_explainer")}</p>

      {showSettings && (
        <div className="space-y-2 p-2 rounded-lg bg-white/[2%] border border-white/[6%]">
          <label className="block text-[10.5px] text-zinc-500">{t("tailscale.admin_api_key_label")}</label>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder={t("tailscale.admin_api_key_placeholder")}
            className="w-full px-2 py-1.5 rounded bg-black/30 border border-white/[8%] text-xs text-zinc-200 font-mono placeholder-zinc-600 focus:outline-none focus:border-emerald-500/40"
          />
          <p className="text-[10px] text-zinc-600">{t("tailscale.admin_api_key_hint")}</p>

          <label className="block text-[10.5px] text-zinc-500 pt-1">{t("tailscale.admin_tailnet_label")}</label>
          <input
            type="text"
            value={tailnet}
            onChange={e => setTailnet(e.target.value)}
            placeholder="-"
            className="w-full px-2 py-1.5 rounded bg-black/30 border border-white/[8%] text-xs text-zinc-200 font-mono focus:outline-none focus:border-emerald-500/40"
          />
          <p className="text-[10px] text-zinc-600">{t("tailscale.admin_tailnet_hint")}</p>

          <button onClick={handleSave} disabled={saving || !apiKey.trim()}
            className="px-3 py-1.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs font-medium hover:bg-emerald-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
            {saving ? t("tailscale.admin_saving") : t("tailscale.admin_save")}
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button onClick={handleGenerate} disabled={!cfg.configured || generating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[4%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[7%] disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <KeyRound size={12} className={generating ? "animate-pulse" : ""} />
          {generating ? t("tailscale.invite_generating") : t("tailscale.invite_button")}
        </button>
      </div>

      {error && <p className="text-xs text-rose-400">{error}</p>}

      {invite?.auth_key && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <code className="flex-1 px-2 py-1.5 rounded bg-black/30 border border-white/[8%] text-[11px] text-zinc-200 font-mono truncate">
              {invite.auth_key}
            </code>
            <button onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-1.5 rounded bg-white/[4%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[7%] transition-colors">
              {copied ? <Check size={11} className="text-emerald-400" /> : <ClipboardCopy size={11} />}
              {copied ? t("tailscale.invite_copied") : t("tailscale.invite_copy")}
            </button>
          </div>
          {invite.expires && (
            <p className="text-[10px] text-zinc-600">
              {t("tailscale.invite_expires_at", { when: new Date(invite.expires).toLocaleString() })}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
