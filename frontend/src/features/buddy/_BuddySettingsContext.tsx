import { useTranslation } from "react-i18next"
import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
}

export function BuddySettingsContext({ config, draft, onChange }: Props) {
  const { t } = useTranslation("buddy")
  const context = draft.context ?? config.context

  return <div className="space-y-4">
    <div>
      <label className="mb-1.5 block text-xs font-semibold text-[#8d9ab0]">{t("context.label")}</label>
      <textarea
        value={context}
        onChange={(event) => onChange({ context: event.target.value })}
        rows={14}
        maxLength={8000}
        placeholder={t("context.placeholder")}
        className="w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 font-mono text-sm leading-relaxed text-[#e8eef8] outline-none placeholder:text-[#59677d] focus:border-[#69d7ff]/60"
      />
      <div className="mt-1 flex items-center justify-between gap-3 text-xs text-[#718097]">
        <p>{t("context.hint")}</p>
        <span className="shrink-0 font-mono">{context.length} / 8000</span>
      </div>
    </div>
    <div className="rounded-[4px] border border-amber-400/25 bg-amber-400/[7%] px-3 py-2 text-xs text-amber-200">
      {t("context.session_warning")}
    </div>
  </div>
}
