import { useState } from "react"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { LlmProvider } from "./api"
import { EMPTY_PROVIDER, KNOWN_PROVIDERS } from "./_llm_providers"

export interface ProviderFormProps {
  existing?: LlmProvider
  onSave: (p: LlmProvider) => void
  onCancel?: () => void
}

export function ProviderForm({ existing, onSave, onCancel }: ProviderFormProps) {
  const { t } = useTranslation("llm")
  const { t: tCommon } = useTranslation("common")
  const isEdit = !!existing
  const initialKnown = existing ? KNOWN_PROVIDERS.find((p) => p.id === existing.id) : null
  const initialKnownModels = new Set(initialKnown?.models ?? [])
  const initialSelected = existing ? existing.models.filter((m) => initialKnownModels.has(m)) : []
  const initialCustom = existing ? existing.models.filter((m) => !initialKnownModels.has(m)).join(", ") : ""

  const [form, setForm] = useState<LlmProvider>(existing ? { ...existing } : { ...EMPTY_PROVIDER })
  const [selectedModels, setSelectedModels] = useState<string[]>(initialSelected)
  const [customModel, setCustomModel] = useState(initialCustom)
  const known = KNOWN_PROVIDERS.find((p) => p.id === form.id)
  const hasOAuth = !!existing?.oauth?.access

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const customs = customModel.split(",").map((s) => s.trim()).filter(Boolean)
    const models = [...selectedModels, ...customs]
    onSave({ ...form, name: form.name || known?.name || form.id, models })
    if (!isEdit) {
      setForm({ ...EMPTY_PROVIDER })
      setSelectedModels([])
      setCustomModel("")
    }
  }

  function toggleModel(m: string) {
    setSelectedModels((cur) => cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m])
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 rounded-xl border border-white/[8%] bg-white/[2%] space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{isEdit ? form.name || form.id : t("providers.add")}</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-zinc-500 mb-1">{t("form.provider_label")}</label>
          <select value={form.id} disabled={isEdit}
            onChange={(e) => { setForm({ ...form, id: e.target.value, name: KNOWN_PROVIDERS.find(p => p.id === e.target.value)?.name ?? "" }); setSelectedModels([]) }}
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50 disabled:opacity-60 disabled:cursor-not-allowed">
            <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
            {KNOWN_PROVIDERS.map((p) => <option key={p.id} value={p.id} className="bg-zinc-900 text-zinc-200">{p.name}</option>)}
            {isEdit && !KNOWN_PROVIDERS.find((p) => p.id === form.id) && (
              <option value={form.id} className="bg-zinc-900 text-zinc-200">{form.name || form.id}</option>
            )}
          </select>
        </div>
        <div>
          <label className="block text-xs text-zinc-500 mb-1">{t("form.api_key")}</label>
          <input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            placeholder={known?.placeholder ?? t("form.api_key")}
            className="w-full px-3 py-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
        </div>
      </div>
      {known && (
        <div>
          <label className="block text-xs text-zinc-500 mb-1.5">{t("form.models_label", { selected: selectedModels.length })}</label>
          <div className="flex flex-wrap gap-1.5">
            {known.models.map((m) => {
              const sel = selectedModels.includes(m)
              return (
                <button key={m} type="button" onClick={() => toggleModel(m)}
                  className={`px-2.5 py-1 rounded-md text-xs font-mono transition-all ${
                    sel ? "bg-violet-500/[15%] border border-violet-500/40 text-violet-200"
                        : "bg-white/[3%] border border-white/[8%] text-zinc-400 hover:text-zinc-200 hover:bg-white/[6%]"
                  }`}>{m}</button>
              )
            })}
          </div>
          <input type="text" value={customModel} onChange={(e) => setCustomModel(e.target.value)}
            placeholder={t("form.custom_model")}
            className="mt-2 w-full px-3 py-1.5 rounded-lg bg-white/[3%] border border-white/[6%] text-zinc-300 text-xs font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/40" />
        </div>
      )}
      {hasOAuth && (
        <p className="text-[11px] text-violet-300/80">
          OAuth-Login aktiv — API-Key-Eingabe optional. OAuth bleibt erhalten.
        </p>
      )}
      <div className="flex items-center gap-2">
        <button type="submit" disabled={!form.id || (!form.api_key && !hasOAuth) || (selectedModels.length === 0 && !customModel.trim())}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-all">
          <Plus size={14} /> {isEdit ? tCommon("actions.save") : tCommon("actions.add")}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors">
            {tCommon("actions.cancel")}
          </button>
        )}
      </div>
    </form>
  )
}
