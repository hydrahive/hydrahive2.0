import { useTranslation } from "react-i18next"

interface Props {
  prompt: string
  onChange: (v: string) => void
}

export function PromptTab({ prompt, onChange }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-1">
      <label className="block text-[10px] font-medium text-zinc-500">{t("fields.system_prompt")}</label>
      <textarea
        value={prompt}
        onChange={(e) => onChange(e.target.value)}
        rows={20}
        className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50"
      />
    </div>
  )
}
