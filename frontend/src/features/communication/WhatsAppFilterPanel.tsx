import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Save, Shield, Check } from "lucide-react"
import { communicationApi, type WhatsAppConfig } from "./api"

const EMPTY: WhatsAppConfig = {
  private_chats_enabled: true,
  group_chats_enabled: false,
  require_keyword: "",
  owner_numbers: [],
  allowed_numbers: [],
  blocked_numbers: [],
  respond_as_voice: false,
  voice_name: "German_FriendlyMan",
  stt_language: "",
}

function toLines(arr: string[]): string {
  return arr.join("\n")
}

function fromLines(text: string): string[] {
  return text.split("\n").map((s) => s.trim()).filter(Boolean)
}

export function WhatsAppFilterPanel() {
  const { t } = useTranslation("communication")
  const [cfg, setCfg] = useState<WhatsAppConfig>(EMPTY)
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const [ownerText, setOwnerText] = useState("")
  const [allowedText, setAllowedText] = useState("")
  const [blockedText, setBlockedText] = useState("")

  useEffect(() => {
    communicationApi.whatsapp.getConfig()
      .then((c) => {
        setCfg(c)
        setOwnerText(toLines(c.owner_numbers))
        setAllowedText(toLines(c.allowed_numbers))
        setBlockedText(toLines(c.blocked_numbers))
        setLoaded(true)
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
  }, [])

  async function save() {
    setSaving(true); setErr(null)
    try {
      const next: WhatsAppConfig = {
        ...cfg,
        owner_numbers: fromLines(ownerText),
        allowed_numbers: fromLines(allowedText),
        blocked_numbers: fromLines(blockedText),
      }
      const saved = await communicationApi.whatsapp.putConfig(next)
      setCfg(saved)
      setOwnerText(toLines(saved.owner_numbers))
      setAllowedText(toLines(saved.allowed_numbers))
      setBlockedText(toLines(saved.blocked_numbers))
      setSavedAt(Date.now())
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) {
    return <p className="text-xs text-zinc-500">{t("whatsapp.filter.loading")}</p>
  }

  const justSaved = savedAt !== null && Date.now() - savedAt < 3000

  return (
    <div className="space-y-3 border-t border-white/[6%] pt-4">
      <div className="flex items-center gap-2 text-xs font-medium text-zinc-300">
        <Shield size={13} className="text-emerald-400" />
        {t("whatsapp.filter.title")}
      </div>
      <p className="text-[11px] text-zinc-500">{t("whatsapp.filter.intro")}</p>

      <div className="flex gap-4">
        <label className="flex items-center gap-1.5 text-xs cursor-pointer text-zinc-300">
          <input type="checkbox" checked={cfg.private_chats_enabled}
            onChange={(e) => setCfg({ ...cfg, private_chats_enabled: e.target.checked })}
            className="h-3 w-3 rounded" />
          {t("whatsapp.filter.private_chats")}
        </label>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer text-zinc-300">
          <input type="checkbox" checked={cfg.group_chats_enabled}
            onChange={(e) => setCfg({ ...cfg, group_chats_enabled: e.target.checked })}
            className="h-3 w-3 rounded" />
          {t("whatsapp.filter.group_chats")}
        </label>
      </div>

      <div>
        <label className="text-[11px] text-zinc-500">{t("whatsapp.filter.keyword_label")}</label>
        <input type="text" value={cfg.require_keyword}
          onChange={(e) => setCfg({ ...cfg, require_keyword: e.target.value })}
          placeholder={t("whatsapp.filter.keyword_placeholder")}
          className="mt-1 w-full rounded-lg bg-white/[3%] border border-white/[8%] px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-violet-500/50" />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <NumberList label={t("whatsapp.filter.owner")} value={ownerText} onChange={setOwnerText}
          hint={t("whatsapp.filter.owner_hint")} />
        <NumberList label={t("whatsapp.filter.allowed")} value={allowedText} onChange={setAllowedText}
          hint={t("whatsapp.filter.allowed_hint")} />
        <NumberList label={t("whatsapp.filter.blocked")} value={blockedText} onChange={setBlockedText}
          hint={t("whatsapp.filter.blocked_hint")} />
      </div>

      <div className="border-t border-white/[6%] pt-3 space-y-2">
        <div>
          <label className="text-[11px] text-zinc-500">Sprache der eingehenden Sprachnachrichten</label>
          <select value={cfg.stt_language || ""}
            onChange={(e) => setCfg({ ...cfg, stt_language: e.target.value })}
            className="mt-1 w-full rounded-lg bg-white/[3%] border border-white/[8%] px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-violet-500/50">
            <option value="">Auto-Erkennung</option>
            <option value="de">Deutsch</option>
            <option value="en">English</option>
            <option value="fr">Français</option>
            <option value="es">Español</option>
            <option value="it">Italiano</option>
          </select>
          <p className="text-[10px] text-zinc-600 mt-1">
            Auto-Erkennung ist robust ab ~3s Audio. Bei sehr kurzen Voices lieber explizit setzen.
          </p>
        </div>

        <label className="flex items-center gap-1.5 text-xs cursor-pointer text-zinc-300">
          <input type="checkbox" checked={cfg.respond_as_voice}
            onChange={(e) => setCfg({ ...cfg, respond_as_voice: e.target.checked })}
            className="h-3 w-3 rounded" />
          Antworten als Sprachnachricht senden
        </label>
        {cfg.respond_as_voice && (
          <div>
            <label className="text-[11px] text-zinc-500">Stimme (MiniMax)</label>
            <input type="text" value={cfg.voice_name}
              onChange={(e) => setCfg({ ...cfg, voice_name: e.target.value })}
              placeholder="German_FriendlyMan"
              className="mt-1 w-full rounded-lg bg-white/[3%] border border-white/[8%] px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-violet-500/50" />
            <p className="text-[10px] text-zinc-600 mt-1">
              Voices anzeigen: Profil → TTS-Card. Beispiele: German_FriendlyMan,
              German_PlayfulGirl, German_SweetLady.
            </p>
          </div>
        )}
      </div>

      {err && (
        <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">{err}</div>
      )}

      <div className="flex justify-end items-center gap-3">
        {justSaved && (
          <span className="flex items-center gap-1 text-xs text-emerald-400">
            <Check size={12} /> {t("whatsapp.filter.saved")}
          </span>
        )}
        <button onClick={save} disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/15 border border-violet-500/30 text-violet-200 text-xs font-medium hover:bg-violet-500/25 disabled:opacity-50 transition-colors">
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          {t("whatsapp.filter.save")}
        </button>
      </div>
    </div>
  )
}

function NumberList({ label, hint, value, onChange }:
  { label: string; hint: string; value: string; onChange: (s: string) => void }) {
  return (
    <div>
      <label className="text-[11px] text-zinc-500">{label}</label>
      <textarea value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={"+49…"} rows={3}
        className="mt-1 w-full rounded-lg bg-white/[3%] border border-white/[8%] px-2.5 py-1.5 text-xs text-zinc-100 font-mono resize-y focus:outline-none focus:border-violet-500/50" />
      <p className="text-[10px] text-zinc-600 mt-1">{hint}</p>
    </div>
  )
}
