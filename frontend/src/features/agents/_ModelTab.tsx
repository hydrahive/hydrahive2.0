import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Agent } from "./types"
import type { RegistryModel } from "@/features/llm/api"

interface Props {
  draft: Agent
  models: string[]
  catalog: RegistryModel[]
  onChange: (patch: Partial<Agent>) => void
}

export function ModelTab({ draft, models, catalog, onChange }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-3">
      <Field label={t("fields.model")}>
        <ModelPicker
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <Field label={t("fields.max_iterations", { count: draft.max_iterations ?? 30 })} hint={t("fields.max_iterations_hint")}>
          <input
            type="number" min="1" max="200" value={draft.max_iterations ?? 30}
            onChange={(e) => onChange({ max_iterations: parseInt(e.target.value) })}
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

function ModelPicker({ value, catalog, onChange }: {
  value: string; catalog: RegistryModel[]; onChange: (m: string) => void
}) {
  const [q, setQ] = useState("")
  const [onlyFree, setOnlyFree] = useState(false)
  const filtered = useMemo(() => catalog.filter((m) =>
    (!onlyFree || m.is_free === true) &&
    (q === "" || m.id.toLowerCase().includes(q.toLowerCase()))
  ).slice(0, 100), [catalog, q, onlyFree])

  return (
    <div className="space-y-1">
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Modell suchen…"
          className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
        <label className="flex items-center gap-1 text-[10px] text-zinc-400 whitespace-nowrap">
          <input type="checkbox" checked={onlyFree} onChange={(e) => setOnlyFree(e.target.checked)} />
          nur gratis
        </label>
      </div>
      <select value={value} onChange={(e) => onChange(e.target.value)} size={6}
        className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono">
        {!filtered.some((m) => m.id === value) && value && <option value={value}>{value} (aktuell)</option>}
        {filtered.map((m) => (
          <option key={m.id} value={m.id}>{m.is_free === true ? "🆓 " : ""}{m.id}</option>
        ))}
      </select>
      {filtered.length === 100 && <p className="text-[10px] text-zinc-600">…verfeinere die Suche (max 100 angezeigt)</p>}
    </div>
  )
}

function providerOf(model: string): string {
  return model.includes("/") ? model.split("/")[0] : "(direkt)"
}

function FallbackModelsSelector({ primary, available, selected, onChange }: {
  primary: string; available: string[]; selected: string[]; onChange: (s: string[]) => void
}) {
  const add = (m: string) => onChange([...selected, m])
  const remove = (m: string) => onChange(selected.filter((x) => x !== m))
  const moveUp = (i: number) => {
    if (i === 0) return
    const next = [...selected]
    ;[next[i - 1], next[i]] = [next[i], next[i - 1]]
    onChange(next)
  }

  // Verbleibende Modelle nach Provider gruppieren → ein Dropdown pro Provider
  // (statt hunderte Buttons untereinander).
  const byProvider = useMemo(() => {
    const map = new Map<string, string[]>()
    for (const m of available) {
      if (m === primary || selected.includes(m)) continue
      const p = providerOf(m)
      ;(map.get(p) ?? map.set(p, []).get(p)!).push(m)
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [available, primary, selected])

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
      {byProvider.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {byProvider.map(([prov, ms]) => (
            <select
              key={prov}
              value=""
              onChange={(e) => { if (e.target.value) add(e.target.value) }}
              className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-300"
            >
              <option value="">+ {prov} ({ms.length})…</option>
              {ms.map((m) => (
                <option key={m} value={m}>{m.includes("/") ? m.split("/").slice(1).join("/") : m}</option>
              ))}
            </select>
          ))}
        </div>
      ) : (
        selected.length === 0 && <p className="text-xs text-zinc-600">—</p>
      )}
    </div>
  )
}
