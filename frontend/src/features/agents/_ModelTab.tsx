import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

interface Props {
  draft: Agent
  models: string[]
  onChange: (patch: Partial<Agent>) => void
}

export function ModelTab({ draft, models, onChange }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <Field label={t("fields.model")}>
          <select
            value={draft.llm_model}
            onChange={(e) => onChange({ llm_model: e.target.value })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          >
            {!models.includes(draft.llm_model) && (
              <option value={draft.llm_model}>{t("fields.model_not_in_config", { model: draft.llm_model })}</option>
            )}
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
        <Field label={t("fields.temperature")}>
          <input
            type="number" step="0.1" min="0" max="2" value={draft.temperature}
            onChange={(e) => onChange({ temperature: parseFloat(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </Field>
        <Field label={t("fields.max_tokens")}>
          <input
            type="number" value={draft.max_tokens}
            onChange={(e) => onChange({ max_tokens: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </Field>
      </div>

      <Field label={t("fields.fallback_models")} hint={t("fields.fallback_hint")}>
        <FallbackModelsSelector
          primary={draft.llm_model}
          available={models}
          selected={draft.fallback_models ?? []}
          onChange={(fb) => onChange({ fallback_models: fb })}
        />
      </Field>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-zinc-600 mt-0.5">{hint}</p>}
    </div>
  )
}

function FallbackModelsSelector({ primary, available, selected, onChange }: {
  primary: string; available: string[]; selected: string[]; onChange: (s: string[]) => void
}) {
  const remaining = available.filter((m) => m !== primary && !selected.includes(m))
  const add = (m: string) => onChange([...selected, m])
  const remove = (m: string) => onChange(selected.filter((x) => x !== m))
  const moveUp = (i: number) => {
    if (i === 0) return
    const next = [...selected]
    ;[next[i - 1], next[i]] = [next[i], next[i - 1]]
    onChange(next)
  }
  return (
    <div className="space-y-2">
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((m, i) => (
            <span key={m} className="inline-flex items-center gap-1 pl-2.5 pr-1 py-1 rounded-md bg-violet-500/15 border border-violet-500/30 text-violet-200 text-xs font-mono">
              <span className="text-[10px] text-violet-400 mr-0.5">{i + 1}.</span>
              {m}
              <button onClick={() => moveUp(i)} disabled={i === 0}
                className="px-1 text-violet-300 hover:text-white disabled:opacity-30" title="hoch">↑</button>
              <button onClick={() => remove(m)}
                className="px-1 text-violet-300 hover:text-rose-300" title="entfernen">×</button>
            </span>
          ))}
        </div>
      )}
      {remaining.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {remaining.map((m) => (
            <button key={m} onClick={() => add(m)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white/[3%] border border-white/[8%] text-zinc-400 hover:text-zinc-100 hover:bg-white/[6%] text-xs font-mono transition-colors">
              + {m}
            </button>
          ))}
        </div>
      )}
      {selected.length === 0 && remaining.length === 0 && (
        <p className="text-xs text-zinc-600">—</p>
      )}
    </div>
  )
}
