import { AlertTriangle } from "lucide-react"
import { useTranslation } from "react-i18next"

interface Props {
  prompt: string
  onChange: (v: string) => void
  /** Soul-Dateien aktiv: der System-Prompt wird dann vom Backend ignoriert. */
  soulActive?: boolean
}

export function PromptTab({ prompt, onChange, soulActive = false }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-1">
      {soulActive ? (
        <p className="mb-2 flex items-start gap-2 rounded-md border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          {t("soul.prompt_inactive")}
        </p>
      ) : null}
      <label className="block text-[10px] font-medium text-zinc-500">{t("fields.system_prompt")}</label>
      <textarea
        value={prompt}
        onChange={(e) => onChange(e.target.value)}
        readOnly={soulActive}
        rows={20}
        className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50 read-only:opacity-60"
      />
    </div>
  )
}
