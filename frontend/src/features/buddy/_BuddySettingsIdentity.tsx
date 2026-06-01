import { useTranslation } from "react-i18next"
import { Dice5 } from "lucide-react"
import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
  onRerollCharacter: () => void
  busy: boolean
}

export function BuddySettingsIdentity({ config, draft, onChange, onRerollCharacter, busy }: Props) {
  const { t } = useTranslation("buddy")
  const name = draft.name ?? config.name
  const language = draft.language ?? config.language
  const tone = draft.tone ?? config.tone

  const LANGUAGE_OPTIONS = [
    { value: "de", label: t("identity.lang_de") },
    { value: "en", label: t("identity.lang_en") },
    { value: "auto", label: t("identity.lang_auto") },
  ]
  const TONE_OPTIONS = [
    { value: "locker", label: t("identity.tone_casual") },
    { value: "professionell", label: t("identity.tone_professional") },
    { value: "knapp", label: t("identity.tone_brief") },
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">{t("identity.name_label")}</label>
        <input
          value={name}
          onChange={(e) => onChange({ name: e.target.value })}
          className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">{t("identity.character_label")}</label>
        <div className="flex items-center gap-3">
          <span className="flex-1 px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-300 text-sm truncate">
            {config.character || "—"}
          </span>
          <button
            onClick={onRerollCharacter}
            disabled={busy}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[8%] text-xs text-zinc-400 hover:text-pink-300 hover:border-pink-500/30 hover:bg-pink-500/[4%] transition-all disabled:opacity-40"
          >
            <Dice5 size={13} />
            🎲
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{t("identity.language_label")}</label>
          <select
            value={language}
            onChange={(e) => onChange({ language: e.target.value as BuddyConfigPatch["language"] })}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
          >
            {LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{t("identity.tone_label")}</label>
          <select
            value={tone}
            onChange={(e) => onChange({ tone: e.target.value as BuddyConfigPatch["tone"] })}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
          >
            {TONE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
    </div>
  )
}
