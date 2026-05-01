import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

interface Props {
  draft: Agent
  onChange: (patch: Partial<Agent>) => void
}

export function OverviewTab({ draft, onChange }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label={t("fields.type")}>
          <p className="px-2 py-1 text-xs text-zinc-300 font-mono">{t(`type.${draft.type}`)}</p>
        </Field>
      </div>
      <Field label={t("fields.description")}>
        <textarea
          value={draft.description}
          onChange={(e) => onChange({ description: e.target.value })}
          rows={3}
          className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50"
        />
      </Field>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
    </div>
  )
}
