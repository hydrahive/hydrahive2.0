import { useTranslation } from "react-i18next"
import type { BuddyConfig, BuddyConfigPatch, CacheTtl } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
  availableModels: string[]
}

const control = "w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"

export function BuddySettingsAdvanced({ config, draft, onChange, availableModels }: Props) {
  const { t } = useTranslation("buddy")
  const model = draft.compact_model ?? config.compact_model
  const threshold = draft.compact_threshold_pct ?? config.compact_threshold_pct
  const models = Array.from(new Set([config.model, model, ...availableModels].filter(Boolean))).sort()

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("advanced.compact_model")}>
          <select value={model} onChange={(event) => onChange({ compact_model: event.target.value })} className={control}>
            <option value="">{t("advanced.main_model", { model: config.model })}</option>
            {models.filter((item) => item !== config.model).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </Field>
        <Field label={t("advanced.threshold", { value: threshold })} hint={t("advanced.threshold_hint")}>
          <input type="range" min={30} max={100} step={5} value={threshold} onChange={(event) => onChange({ compact_threshold_pct: Number(event.target.value) })} className="mt-2 w-full accent-[#69d7ff]" />
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <NumberField label={t("advanced.compact_tool_limit")} value={draft.compact_tool_result_limit ?? config.compact_tool_result_limit} min={100} max={50000} step={100} onChange={(value) => onChange({ compact_tool_result_limit: value })} />
        <NumberField label={t("advanced.reserve_tokens")} value={draft.compact_reserve_tokens ?? config.compact_reserve_tokens} min={1000} max={100000} step={1000} onChange={(value) => onChange({ compact_reserve_tokens: value })} />
        <Field label={t("advanced.max_turns")} hint={t("advanced.max_turns_hint")}>
          <input type="number" min={1000} max={100000} step={500} value={draft.compact_max_turns !== undefined ? draft.compact_max_turns ?? "" : config.compact_max_turns ?? ""} placeholder={t("advanced.automatic")} onChange={(event) => onChange({ compact_max_turns: event.target.value === "" ? null : Number(event.target.value) })} className={control} />
        </Field>
        <NumberField label={t("advanced.tool_result_max")} hint={t("advanced.zero_unlimited")} value={draft.tool_result_max_chars ?? config.tool_result_max_chars} min={0} max={1000000} step={1000} onChange={(value) => onChange({ tool_result_max_chars: value })} />
        <NumberField label={t("advanced.max_iterations")} value={draft.max_iterations ?? config.max_iterations} min={1} max={250} onChange={(value) => onChange({ max_iterations: value })} />
        <Field label={t("advanced.cache_ttl")}>
          <select value={draft.cache_ttl ?? config.cache_ttl} onChange={(event) => onChange({ cache_ttl: event.target.value as CacheTtl })} className={control}>
            <option value="5m">5m</option><option value="1h">1h</option>
          </select>
        </Field>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return <div><label className="mb-1 block text-xs font-semibold text-[#8d9ab0]">{label}</label>{children}{hint && <p className="mt-1 text-[11px] text-[#718097]">{hint}</p>}</div>
}

function NumberField({ label, hint, value, min, max, step = 1, onChange }: { label: string; hint?: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) {
  return <Field label={label} hint={hint}><input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} className={control} /></Field>
}
