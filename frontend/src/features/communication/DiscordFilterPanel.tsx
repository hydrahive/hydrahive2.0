import { useEffect, useState } from "react"
import { Check, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import { communicationApi, type DiscordConfig } from "./api"

const DEFAULT_CFG: DiscordConfig = {
  bot_token: "",
  dm_enabled: true,
  mention_enabled: true,
  require_keyword: "",
  allowed_user_ids: [],
  blocked_user_ids: [],
  allowed_channel_ids: [],
  respond_as_voice: false,
  voice_name: "German_FriendlyMan",
}

function toLines(ids: string[]) { return ids.join("\n") }
function fromLines(s: string) { return s.split("\n").map((l) => l.trim()).filter(Boolean) }

export function DiscordFilterPanel() {
  const { t } = useTranslation("communication")
  const [cfg, setCfg] = useState<DiscordConfig>(DEFAULT_CFG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [tokenInput, setTokenInput] = useState("")

  useEffect(() => {
    communicationApi.discord.getConfig()
      .then((c) => { setCfg(c); setTokenInput(c.bot_token) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    setSaving(true)
    try {
      const updated = await communicationApi.discord.putConfig({
        ...cfg,
        bot_token: tokenInput,
      })
      setCfg(updated)
      setTokenInput(updated.bot_token)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-xs text-zinc-500">{t("discord.filter.loading")}</p>

  return (
    <div className="space-y-4 pt-2 border-t border-white/[6%]">
      <p className="text-[10px] text-zinc-500">{t("discord.filter.intro")}</p>

      {/* Token */}
      <div className="space-y-1">
        <label className="text-xs text-zinc-400">{t("discord.filter.token_label")}</label>
        <input
          type="password"
          value={tokenInput === "***" ? "" : tokenInput}
          placeholder={tokenInput === "***" ? "••••••••••••••••" : t("discord.filter.token_placeholder")}
          onChange={(e) => setTokenInput(e.target.value)}
          className="w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-violet-500/50 font-mono"
        />
        <p className="text-[10px] text-zinc-600">{t("discord.filter.token_hint")}</p>
      </div>

      {/* Toggles */}
      <div className="flex gap-4">
        {(["dm_enabled", "mention_enabled"] as const).map((key) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={cfg[key]}
              onChange={(e) => setCfg({ ...cfg, [key]: e.target.checked })}
              className="accent-[var(--hh-accent-from)] w-3.5 h-3.5"
            />
            <span className="text-xs text-zinc-300">
              {t(`discord.filter.${key === "dm_enabled" ? "dm_enabled" : "mention_enabled"}`)}
            </span>
          </label>
        ))}
      </div>

      {/* Keyword */}
      <div className="space-y-1">
        <label className="text-xs text-zinc-400">{t("discord.filter.keyword_label")}</label>
        <input
          value={cfg.require_keyword}
          placeholder={t("discord.filter.keyword_placeholder")}
          onChange={(e) => setCfg({ ...cfg, require_keyword: e.target.value })}
          className="w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-violet-500/50"
        />
      </div>

      {/* ID Lists */}
      {(
        [
          ["allowed_user_ids", "allowed_users", "allowed_users_hint"],
          ["blocked_user_ids", "blocked_users", "blocked_users_hint"],
          ["allowed_channel_ids", "allowed_channels", "allowed_channels_hint"],
        ] as const
      ).map(([field, label, hint]) => (
        <div key={field} className="space-y-1">
          <label className="text-xs text-zinc-400">{t(`discord.filter.${label}`)}</label>
          <textarea
            value={toLines(cfg[field])}
            onChange={(e) => setCfg({ ...cfg, [field]: fromLines(e.target.value) })}
            rows={3}
            className="w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none focus:border-violet-500/50 resize-y"
          />
          <p className="text-[10px] text-zinc-600">{t(`discord.filter.${hint}`)}</p>
        </div>
      ))}

      {/* Voice */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={cfg.respond_as_voice}
          onChange={(e) => setCfg({ ...cfg, respond_as_voice: e.target.checked })}
          className="accent-[var(--hh-accent-from)] w-3.5 h-3.5"
        />
        <span className="text-xs text-zinc-300">{t("discord.filter.voice_label")}</span>
      </label>

      <button
        onClick={handleSave}
        disabled={saving}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border transition-colors disabled:opacity-30 ${
          saved
            ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
            : "border-white/[8%] text-zinc-300 hover:text-white hover:bg-white/[5%]"
        }`}
      >
        {saved ? <Check size={12} /> : <Save size={12} />}
        {saved ? t("discord.filter.saved") : t("discord.filter.save")}
      </button>
    </div>
  )
}
