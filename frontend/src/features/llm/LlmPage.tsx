import { useEffect, useState } from "react"
import { CheckCircle, Loader2, Pencil, Plus, Trash2, XCircle, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { llmApi, type LlmConfig, type LlmProvider } from "./api"

const KNOWN_PROVIDERS = [
  {
    id: "anthropic", name: "Anthropic", placeholder: "sk-ant-...",
    models: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5", "claude-sonnet-4-5", "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"],
  },
  {
    id: "openai", name: "OpenAI", placeholder: "sk-...",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
  },
  {
    id: "openrouter", name: "OpenRouter", placeholder: "sk-or-...",
    models: ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "google/gemini-2.0-flash-exp", "deepseek/deepseek-r1", "meta-llama/llama-3.3-70b-instruct"],
  },
  {
    id: "groq", name: "Groq", placeholder: "gsk_...",
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"],
  },
  {
    id: "mistral", name: "Mistral", placeholder: "...",
    models: ["mistral-large-latest", "mistral-small-latest", "codestral-latest", "open-mistral-nemo"],
  },
  {
    id: "gemini", name: "Google Gemini", placeholder: "AIza...",
    models: ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"],
  },
  {
    id: "minimax", name: "MiniMax", placeholder: "eyJ...",
    models: ["MiniMax-M2", "MiniMax-M2.7", "abab6.5s-chat"],
  },
  {
    id: "nvidia", name: "NVIDIA NIM", placeholder: "nvapi-...",
    models: [
      "nvidia_nim/qwen/qwen2.5-coder-32b-instruct",
      "nvidia_nim/mistralai/codestral-22b-v0.1",
      "nvidia_nim/bigcode/starcoder2-15b",
      "nvidia_nim/qwen/qwq-32b-preview",
      "nvidia_nim/deepseek-ai/deepseek-r1",
      "nvidia_nim/meta/llama-3.3-70b-instruct",
      "nvidia_nim/meta/llama-3.1-405b-instruct",
      "nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct",
      "nvidia_nim/mistralai/mistral-large-2-instruct",
    ],
  },
]

const EMPTY_PROVIDER: LlmProvider = { id: "", name: "", api_key: "", models: [] }

function ProviderCard({ provider, onEdit, onDelete }: { provider: LlmProvider; onEdit: () => void; onDelete: () => void }) {
  const { t } = useTranslation("llm")
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-white/[8%] bg-white/[3%]">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200">{provider.name || provider.id}</p>
        <p className="text-xs text-zinc-500 mt-0.5">
          {provider.api_key ? "••••••••" + provider.api_key.slice(-4) : t("providers.no_key")}
          {" · "}
          {t("providers.models_count", { count: provider.models.length })}
        </p>
      </div>
      <button onClick={onEdit}
        className="p-1.5 rounded-lg text-zinc-600 hover:text-violet-300 hover:bg-violet-500/10 transition-colors">
        <Pencil size={14} />
      </button>
      <button onClick={onDelete}
        className="p-1.5 rounded-lg text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
        <Trash2 size={14} />
      </button>
    </div>
  )
}

interface ProviderFormProps {
  existing?: LlmProvider
  onSave: (p: LlmProvider) => void
  onCancel?: () => void
}

function ProviderForm({ existing, onSave, onCancel }: ProviderFormProps) {
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

      <div className="flex items-center gap-2">
        <button type="submit" disabled={!form.id || !form.api_key || (selectedModels.length === 0 && !customModel.trim())}
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

export function LlmPage() {
  const { t } = useTranslation("llm")
  const { t: tCommon } = useTranslation("common")
  const [config, setConfig] = useState<LlmConfig>({ providers: [], default_model: "" })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [editingIdx, setEditingIdx] = useState<number | null>(null)

  const allModels = config.providers.flatMap((p) => p.models)

  useEffect(() => { llmApi.getConfig().then(setConfig).catch(() => {}) }, [])

  async function save(next: LlmConfig) {
    setSaving(true)
    try { const saved = await llmApi.updateConfig(next); setConfig(saved) }
    finally { setSaving(false) }
  }

  async function testConnection() {
    setTesting(true); setTestResult(null)
    try {
      const r = await llmApi.testConnection(config.default_model || undefined)
      setTestResult({ ok: true, msg: r.response })
    } catch (e) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : tCommon("status.error") })
    } finally { setTesting(false) }
  }

  function addProvider(p: LlmProvider) {
    const next = { ...config, providers: [...config.providers, p] }
    setConfig(next); save(next); setShowAdd(false)
  }

  function updateProvider(idx: number, p: LlmProvider) {
    const next = { ...config, providers: config.providers.map((cur, i) => i === idx ? p : cur) }
    setConfig(next); save(next); setEditingIdx(null)
  }

  function deleteProvider(idx: number) {
    const next = { ...config, providers: config.providers.filter((_, i) => i !== idx) }
    setConfig(next); save(next)
    if (editingIdx === idx) setEditingIdx(null)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <HelpButton topic="llm" />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("providers.title")}</p>
          <button onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors">
            <Plus size={13} /> {tCommon("actions.add")}
          </button>
        </div>
        {config.providers.length === 0 && !showAdd && (
          <p className="text-sm text-zinc-600 py-4 text-center">{t("providers.none")}</p>
        )}
        {config.providers.map((p, i) => (
          editingIdx === i
            ? <ProviderForm key={i} existing={p}
                onSave={(updated) => updateProvider(i, updated)}
                onCancel={() => setEditingIdx(null)} />
            : <ProviderCard key={i} provider={p}
                onEdit={() => setEditingIdx(i)}
                onDelete={() => deleteProvider(i)} />
        ))}
        {showAdd && <ProviderForm onSave={addProvider} onCancel={() => setShowAdd(false)} />}
      </div>

      {allModels.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("default_model")}</p>
          <select value={config.default_model}
            onChange={(e) => { const next = { ...config, default_model: e.target.value }; setConfig(next); save(next) }}
            className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
            <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
            {allModels.map((m) => <option key={m} value={m} className="bg-zinc-900 text-zinc-200">{m}</option>)}
          </select>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button onClick={testConnection} disabled={testing || !config.default_model}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-900/20">
          {testing ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
          {t("test.button")}
        </button>
        {saving && <span className="text-xs text-zinc-500">{t("test.saving")}</span>}
        {testResult && (
          <span className={`flex items-center gap-1.5 text-sm ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}>
            {testResult.ok ? <CheckCircle size={15} /> : <XCircle size={15} />}
            {testResult.ok ? t("test.ok", { response: testResult.msg }) : testResult.msg}
          </span>
        )}
      </div>
    </div>
  )
}
