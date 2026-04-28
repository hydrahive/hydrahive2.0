import { useEffect, useState } from "react"
import { CheckCircle, Loader2, Plus, Trash2, XCircle, Zap } from "lucide-react"
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
]

const EMPTY_PROVIDER: LlmProvider = { id: "", name: "", api_key: "", models: [] }

function ProviderCard({ provider, onDelete }: { provider: LlmProvider; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-white/[8%] bg-white/[3%]">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200">{provider.name || provider.id}</p>
        <p className="text-xs text-zinc-500 mt-0.5">
          {provider.api_key ? "••••••••" + provider.api_key.slice(-4) : "Kein Key"}
          {" · "}
          {provider.models.length} Modell{provider.models.length !== 1 ? "e" : ""}
        </p>
      </div>
      <button onClick={onDelete}
        className="p-1.5 rounded-lg text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
        <Trash2 size={14} />
      </button>
    </div>
  )
}

function AddProviderForm({ onAdd }: { onAdd: (p: LlmProvider) => void }) {
  const [form, setForm] = useState<LlmProvider>({ ...EMPTY_PROVIDER })
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [customModel, setCustomModel] = useState("")
  const known = KNOWN_PROVIDERS.find((p) => p.id === form.id)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const models = customModel.trim() ? [...selectedModels, customModel.trim()] : selectedModels
    onAdd({ ...form, name: form.name || known?.name || form.id, models })
    setForm({ ...EMPTY_PROVIDER })
    setSelectedModels([])
    setCustomModel("")
  }

  function toggleModel(m: string) {
    setSelectedModels((cur) => cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m])
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 rounded-xl border border-white/[8%] bg-white/[2%] space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Provider hinzufügen</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Provider</label>
          <select value={form.id} onChange={(e) => { setForm({ ...form, id: e.target.value, name: KNOWN_PROVIDERS.find(p => p.id === e.target.value)?.name ?? "" }); setSelectedModels([]) }}
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
            <option value="" className="bg-zinc-900 text-zinc-400">Auswählen…</option>
            {KNOWN_PROVIDERS.map((p) => <option key={p.id} value={p.id} className="bg-zinc-900 text-zinc-200">{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-zinc-500 mb-1">API Key</label>
          <input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            placeholder={known?.placeholder ?? "API Key"}
            className="w-full px-3 py-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
        </div>
      </div>

      {known && (
        <div>
          <label className="block text-xs text-zinc-500 mb-1.5">Modelle ({selectedModels.length} ausgewählt)</label>
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
            placeholder="oder Custom-Modell eingeben…"
            className="mt-2 w-full px-3 py-1.5 rounded-lg bg-white/[3%] border border-white/[6%] text-zinc-300 text-xs font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/40" />
        </div>
      )}

      <button type="submit" disabled={!form.id || !form.api_key || (selectedModels.length === 0 && !customModel.trim())}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-all">
        <Plus size={14} /> Hinzufügen
      </button>
    </form>
  )
}

export function LlmPage() {
  const [config, setConfig] = useState<LlmConfig>({ providers: [], default_model: "" })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [showAdd, setShowAdd] = useState(false)

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
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : "Fehler" })
    } finally { setTesting(false) }
  }

  function addProvider(p: LlmProvider) {
    const next = { ...config, providers: [...config.providers, p] }
    setConfig(next); save(next); setShowAdd(false)
  }

  function deleteProvider(idx: number) {
    const next = { ...config, providers: config.providers.filter((_, i) => i !== idx) }
    setConfig(next); save(next)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-white">LLM-Konfiguration</h1>
        <p className="text-zinc-500 text-sm mt-0.5">Provider, API-Keys und Standard-Modell</p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Provider</p>
          <button onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors">
            <Plus size={13} /> Hinzufügen
          </button>
        </div>
        {config.providers.length === 0 && !showAdd && (
          <p className="text-sm text-zinc-600 py-4 text-center">Noch kein Provider konfiguriert</p>
        )}
        {config.providers.map((p, i) => (
          <ProviderCard key={i} provider={p} onDelete={() => deleteProvider(i)} />
        ))}
        {showAdd && <AddProviderForm onAdd={addProvider} />}
      </div>

      {allModels.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Standard-Modell</p>
          <select value={config.default_model}
            onChange={(e) => { const next = { ...config, default_model: e.target.value }; setConfig(next); save(next) }}
            className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
            <option value="" className="bg-zinc-900 text-zinc-400">Auswählen…</option>
            {allModels.map((m) => <option key={m} value={m} className="bg-zinc-900 text-zinc-200">{m}</option>)}
          </select>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button onClick={testConnection} disabled={testing || !config.default_model}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-900/20">
          {testing ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
          Verbindung testen
        </button>
        {saving && <span className="text-xs text-zinc-500">Speichern…</span>}
        {testResult && (
          <span className={`flex items-center gap-1.5 text-sm ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}>
            {testResult.ok ? <CheckCircle size={15} /> : <XCircle size={15} />}
            {testResult.ok ? `OK · "${testResult.msg}"` : testResult.msg}
          </span>
        )}
      </div>
    </div>
  )
}
