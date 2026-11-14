import { useTranslation } from "react-i18next"
import type { Agent } from "./types"
import type { RegistryModel } from "@/features/llm/api"
import { TemplateBinding } from "./_TemplateBinding"

interface Props {
  draft: Agent
  /** Nicht mehr genutzt (Modell kommt aus dem Template); bleibt für bestehende Aufrufer optional. */
  catalog?: RegistryModel[]
  onChange: (patch: Partial<Agent>) => void
}

export function ModelTab({ draft, onChange }: Props) {
  // Aufräumen 14.11.2026: Modell, Fallback und Budget kommen nur noch aus dem Agenten-Template (LLM-Seite).
  return (
    <div className="space-y-3">
      <TemplateBinding value={draft.template} onChange={(template) => onChange({ template })} />
      <TemperatureOnly draft={draft} onChange={onChange} />
    </div>
  )
}

/** Gebunden: nur noch Temperatur (nicht Teil des Templates). */
function TemperatureOnly({ draft, onChange }: { draft: Agent; onChange: (patch: Partial<Agent>) => void }) {
  const { t } = useTranslation("agents")
  return (
    <Field label={t("fields.temperature")}>
      <input
        type="number" step="0.1" min="0" max="2" value={draft.temperature}
        onChange={(e) => onChange({ temperature: parseFloat(e.target.value) })}
        className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
      />
    </Field>
  )
}

function Field({ label, hint, hintTone, children }: {
  label: string; hint?: string; hintTone?: "warn"; children: React.ReactNode
}) {
  const hintClass = hintTone === "warn" ? "text-amber-400" : "text-zinc-500"
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
      {hint && <p className={`text-[10px] ${hintClass} mt-0.5`}>{hint}</p>}
    </div>
  )
}
