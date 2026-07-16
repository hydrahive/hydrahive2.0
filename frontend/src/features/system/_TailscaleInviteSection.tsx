import { Check, ClipboardCopy, KeyRound, Settings2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import {
  AdminAction,
  AdminFeedback,
  AdminField,
  adminInputClass,
} from "@/features/cockpit/admin/ui"

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

  useEffect(() => {
    async function load() { await loadConfig() }
    load()
  }, [])

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
    <div className="space-y-3 border-t border-[#2a364b] pt-3">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">
          <KeyRound size={11} className="text-[#69d7ff]" /> {t("tailscale.invite_title")}
        </p>
        <AdminAction
          onClick={() => setShowSettings(s => !s)}
          tone="ghost"
          className="px-2 py-1 text-[10px]"
        >
          <Settings2 size={10} />
          {cfg.configured ? t("tailscale.admin_configured") : t("tailscale.admin_not_configured")}
        </AdminAction>
      </div>

      <p className="text-[11px] text-[#8d9ab0]">{t("tailscale.invite_explainer")}</p>

      {showSettings && (
        <div className="space-y-3 rounded-[4px] border border-[#2a364b] bg-[#131b2a] p-3">
          <AdminField
            label={t("tailscale.admin_api_key_label")}
            help={t("tailscale.admin_api_key_hint")}
          >
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={t("tailscale.admin_api_key_placeholder")}
              className={`${adminInputClass} font-mono`}
            />
          </AdminField>

          <AdminField
            label={t("tailscale.admin_tailnet_label")}
            help={t("tailscale.admin_tailnet_hint")}
          >
            <input
              type="text"
              value={tailnet}
              onChange={e => setTailnet(e.target.value)}
              placeholder="-"
              className={`${adminInputClass} font-mono`}
            />
          </AdminField>

          <AdminAction onClick={handleSave} disabled={saving || !apiKey.trim()} tone="primary">
            {saving ? t("tailscale.admin_saving") : t("tailscale.admin_save")}
          </AdminAction>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <AdminAction onClick={handleGenerate} disabled={!cfg.configured || generating}>
          <KeyRound size={12} className={generating ? "animate-pulse" : ""} />
          {generating ? t("tailscale.invite_generating") : t("tailscale.invite_button")}
        </AdminAction>
      </div>

      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}

      {invite?.auth_key && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 font-mono text-[11px] text-[#e8eef8]">
              {invite.auth_key}
            </code>
            <AdminAction onClick={handleCopy}>
              {copied ? <Check size={11} className="text-emerald-400" /> : <ClipboardCopy size={11} />}
              {copied ? t("tailscale.invite_copied") : t("tailscale.invite_copy")}
            </AdminAction>
          </div>
          {invite.expires && (
            <p className="text-[10px] text-[#5b6675]">
              {t("tailscale.invite_expires_at", { when: new Date(invite.expires).toLocaleString() })}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
