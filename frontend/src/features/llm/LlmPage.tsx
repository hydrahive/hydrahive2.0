import { useEffect, useState } from "react"
import { BookOpen, CheckCircle, Loader2, Plus, XCircle, Zap } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { llmApi, type EmbedModel, type LlmConfig, type LlmProvider } from "./api"
import { ProviderCard } from "./ProviderCard"
import { ProviderForm } from "./ProviderForm"

export function LlmPage() {
  const { t } = useTranslation("llm")
  const { t: tCommon } = useTranslation("common")
  const [config, setConfig] = useState<LlmConfig>({ providers: [], default_model: "", embed_model: "" })
  const [embedModels, setEmbedModels] = useState<EmbedModel[]>([])
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [editingIdx, setEditingIdx] = useState<number | null>(null)

  const allModels = config.providers.flatMap((p) => p.models)

  useEffect(() => {
    llmApi.getConfig().then(setConfig).catch(() => {})
    llmApi.getEmbedModels().then(setEmbedModels).catch(() => {})
  }, [])

  async function save(next: LlmConfig) {
    setSaving(true)
    try {
      const saved = await llmApi.updateConfig(next)
      setConfig(saved)
      llmApi.getEmbedModels().then(setEmbedModels).catch(() => {})
    } finally { setSaving(false) }
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
        <div className="flex items-center gap-2">
          <Link to="/llm/catalog"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-violet-300 hover:text-violet-200 hover:bg-violet-500/10 border border-violet-500/30">
            <BookOpen size={13} /> Modell-Catalog
          </Link>
          <HelpButton topic="llm" />
        </div>
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

      {embedModels.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("embed_model")}</p>
          <select value={config.embed_model}
            onChange={(e) => { const next = { ...config, embed_model: e.target.value }; setConfig(next); save(next) }}
            className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
            <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
            {embedModels.map((m) => (
              <option key={m.model} value={m.model} className="bg-zinc-900 text-zinc-200">
                {m.model} ({m.dim}d)
              </option>
            ))}
          </select>
          {config.embed_model && (
            <p className="text-[11px] text-zinc-600">
              {t("embed_model_hint", { dim: embedModels.find(m => m.model === config.embed_model)?.dim ?? "?" })}
            </p>
          )}
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
