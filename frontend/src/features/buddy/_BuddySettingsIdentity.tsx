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
        <label className="block text-xs font-medium text-[#8d9ab0]">{t("identity.name_label")}</label>
        <input
          value={name}
          onChange={(e) => onChange({ name: e.target.value })}
          className="w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-[#8d9ab0]">{t("identity.character_label")}</label>
        <div className="flex items-center gap-3">
          <span className="flex-1 truncate rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#d7deea]">
            {config.character || "—"}
          </span>
          <button
            onClick={onRerollCharacter}
            disabled={busy}
            className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-2 text-xs text-[#8d9ab0] hover:border-[#69d7ff]/45 hover:text-[#c8f2ff] disabled:opacity-40"
          >
            <Dice5 size={13} />
            🎲
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-[#8d9ab0]">{t("identity.language_label")}</label>
          <select
            value={language}
            onChange={(e) => onChange({ language: e.target.value as BuddyConfigPatch["language"] })}
            className="w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
          >
            {LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-[#8d9ab0]">{t("identity.tone_label")}</label>
          <select
            value={tone}
            onChange={(e) => onChange({ tone: e.target.value as BuddyConfigPatch["tone"] })}
            className="w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
          >
            {TONE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
    </div>
  )
}
