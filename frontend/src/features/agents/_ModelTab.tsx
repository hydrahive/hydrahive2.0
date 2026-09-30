import { useTranslation } from "react-i18next"
import type { Agent } from "./types"
import type { RegistryModel } from "@/features/llm/api"
import { AgentModelPicker } from "./_AgentModelPicker"
import { FallbackModelsSelector } from "./_FallbackModelsSelector"

interface Props {
  draft: Agent
  catalog: RegistryModel[]
  onChange: (patch: Partial<Agent>) => void
}

export function ModelTab({ draft, catalog, onChange }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-3">
      <Field label={t("fields.model")}>
        <AgentModelPicker
          value={draft.llm_model}
          catalog={catalog}
          onChange={(m) => onChange({ llm_model: m })}
        />
      </Field>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Field label={t("fields.temperature")}>
          <input
            type="number" step="0.1" min="0" max="2" value={draft.temperature}
            onChange={(e) => onChange({ temperature: parseFloat(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </Field>
        <Field
          label={t("fields.max_tokens")}
          hint={
            draft.max_tokens < 8000 && draft.thinking_budget > 0
              ? t("fields.max_tokens_thinking_warning")
              : undefined
          }
          hintTone={
            draft.max_tokens < 8000 && draft.thinking_budget > 0 ? "warn" : undefined
          }
        >
          <input
            type="number" value={draft.max_tokens}
            onChange={(e) => onChange({ max_tokens: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </Field>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Field label={t("fields.max_iterations", { count: draft.max_iterations ?? 16 })} hint={t("fields.max_iterations_hint")}>
          <input
            type="number" min="1" max="250" value={draft.max_iterations ?? 16}
            onChange={(e) => onChange({ max_iterations: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </Field>
        <Field label={t("fields.handoff_timeout")} hint={t("fields.handoff_timeout_hint")}>
          <input
            type="number" min="30" max="3600" value={draft.handoff_timeout_seconds ?? 540}
            onChange={(e) => onChange({ handoff_timeout_seconds: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </Field>
      </div>

      <Field label={t("fields.fallback_models")} hint={t("fields.fallback_hint")}>
        <FallbackModelsSelector
          primary={draft.llm_model}
          catalog={catalog}
          selected={draft.fallback_models ?? []}
          onChange={(fb) => onChange({ fallback_models: fb })}
        />
      </Field>

      <Field
        label={t("fields.thinking_budget", { tokens: draft.thinking_budget })}
        hint={t("fields.thinking_hint")}
      >
        <input
          type="range"
          min={0}
          max={32000}
          step={1024}
          value={draft.thinking_budget}
          onChange={(e) => onChange({ thinking_budget: parseInt(e.target.value) })}
          className="w-full"
        />
      </Field>
    </div>
  )
}

function Field({ label, hint, hintTone, children }: {
  label: string; hint?: string; hintTone?: "warn"; children: React.ReactNode
}) {
  const hintClass = hintTone === "warn" ? "text-amber-400" : "text-zinc-600"
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
      {hint && <p className={`text-[10px] ${hintClass} mt-0.5`}>{hint}</p>}
    </div>
  )
}
