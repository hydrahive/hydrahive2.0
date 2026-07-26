import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { BuddyConfig, BuddyConfigPatch, ReasoningEffort } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
  availableModels: string[]
}

const control = "w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"

export function BuddySettingsModel({ config, draft, onChange, availableModels }: Props) {
  const { t } = useTranslation("buddy")
  const [query, setQuery] = useState("")
  const model = draft.model ?? config.model
  const fallbacks = draft.fallback_models ?? config.fallback_models
  const models = useMemo(
    () => Array.from(new Set([model, ...fallbacks, ...availableModels].filter(Boolean))).sort(),
    [availableModels, fallbacks, model],
  )
  const filtered = models.filter((item) => item.toLowerCase().includes(query.toLowerCase()))

  function toggleFallback(value: string) {
    const next = fallbacks.includes(value) ? fallbacks.filter((item) => item !== value) : [...fallbacks, value].slice(0, 10)
    onChange({ fallback_models: next })
  }

  return (
    <div className="space-y-6">
      <Field label={t("model.primary")} hint={t("model.primary_hint")}>
        <select value={model} onChange={(event) => onChange({ model: event.target.value, reasoning_effort: "" })} className={control}>
          {models.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </Field>

      <div>
        <div className="mb-2 flex items-end justify-between gap-3">
          <div>
            <label className="text-xs font-semibold text-[#8d9ab0]">{t("model.fallbacks")}</label>
            <p className="text-[11px] text-[#718097]">{t("model.fallbacks_hint")}</p>
          </div>
          <span className="text-xs tabular-nums text-[#8d9ab0]">{fallbacks.length}/10</span>
        </div>
        <label className="mb-2 flex items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2">
          <Search size={14} className="text-[#718097]" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("model.search_models")} className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] outline-none placeholder:text-[#59677d]" />
        </label>
        <div className="grid max-h-56 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          {filtered.filter((item) => item !== model).map((item) => {
            const checked = fallbacks.includes(item)
            return <button key={item} type="button" onClick={() => toggleFallback(item)} className={`rounded-[4px] border p-2 text-left text-xs font-mono ${checked ? "border-[#69d7ff]/50 bg-[#163248] text-[#c8f2ff]" : "border-[#2a364b] bg-[#111827] text-[#8d9ab0] hover:border-[#46617f]"}`}>{item}</button>
          })}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("model.temperature")} hint={t("model.temperature_hint")}>
          <input type="number" min={0} max={2} step={0.1} value={draft.temperature ?? config.temperature} onChange={(event) => onChange({ temperature: Number(event.target.value) })} className={control} />
        </Field>
        <Field label={t("model.max_tokens")}>
          <input type="number" min={1} max={200000} value={draft.max_tokens ?? config.max_tokens} onChange={(event) => onChange({ max_tokens: Number(event.target.value) })} className={control} />
        </Field>
        <Field label={t("model.thinking_budget")} hint={t("model.thinking_hint")}>
          <input type="number" min={0} max={200000} value={draft.thinking_budget ?? config.thinking_budget} onChange={(event) => onChange({ thinking_budget: Number(event.target.value) })} className={control} />
        </Field>
        <Field label={t("model.reasoning_effort")}>
          <select value={draft.reasoning_effort ?? config.reasoning_effort} onChange={(event) => onChange({ reasoning_effort: event.target.value as ReasoningEffort })} className={control}>
            <option value="">{t("model.effort_default")}</option>
            <option value="low">{t("model.effort_low")}</option>
            <option value="medium">{t("model.effort_medium")}</option>
            <option value="high">{t("model.effort_high")}</option>
          </select>
        </Field>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return <div><label className="mb-1 block text-xs font-semibold text-[#8d9ab0]">{label}</label>{children}{hint && <p className="mt-1 text-[11px] text-[#718097]">{hint}</p>}</div>
}
