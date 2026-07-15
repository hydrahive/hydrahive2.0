import { useEffect, useState } from "react"
import { BookOpen, CheckCircle, Loader2, Plus, XCircle, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"
import { llmApi, type LlmConfig, type LlmProvider } from "@/features/llm/api"
import { ProviderCard } from "@/features/llm/ProviderCard"
import { ProviderForm } from "@/features/llm/ProviderForm"
import { AnthropicUsageCard } from "@/features/llm/AnthropicUsageCard"
import { DefaultModelsSection } from "@/features/llm/DefaultModelsSection"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

export function LlmOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("llm")
  const { t: tCommon } = useTranslation("common")
  const [config, setConfig] = useState<LlmConfig>({ providers: [], default_model: "", embed_model: "", media_models: {} })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [editingIdx, setEditingIdx] = useState<number | null>(null)

  useEffect(() => { llmApi.getConfig().then(setConfig).catch(() => {}) }, [])

  async function reloadConfig() {
    try { setConfig(await llmApi.getConfig()) } catch (e) { console.error("LLM-Config-Reload fehlgeschlagen:", e) }
  }
  async function save(next: LlmConfig) {
    setSaving(true)
    try { setConfig(await llmApi.updateConfig(next)) } finally { setSaving(false) }
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
  function addProvider(p: LlmProvider) { const next = { ...config, providers: [...config.providers, p] }; setConfig(next); save(next); setShowAdd(false) }
  function updateProvider(idx: number, p: LlmProvider) { const next = { ...config, providers: config.providers.map((cur, i) => i === idx ? p : cur) }; setConfig(next); save(next); setEditingIdx(null) }
  function deleteProvider(idx: number) {
    const next = { ...config, providers: config.providers.filter((_, i) => i !== idx) }
    setConfig(next); save(next)
    if (editingIdx === idx) setEditingIdx(null)
  }

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-3xl"
      headerActions={
        <CockpitButton onClick={() => window.open("/llm/catalog", "_self")}>
          <BookOpen size={13} className="mr-1 inline" />Modell-Catalog
        </CockpitButton>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>

        <AnthropicUsageCard />

        <div className="space-y-2">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#8d9ab0]">{t("providers.title")}</p>
            <button onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-1.5 rounded-[4px] px-3 py-1.5 text-xs text-[#8d9ab0] transition-colors hover:bg-white/5 hover:text-[#e8eef8]">
              <Plus size={13} /> {tCommon("actions.add")}
            </button>
          </div>
          {config.providers.length === 0 && !showAdd && (
            <p className="py-4 text-center text-sm text-[#8d9ab0]">{t("providers.none")}</p>
          )}
          {config.providers.map((p, i) => (
            editingIdx === i
              ? <ProviderForm key={i} existing={p}
                  onSave={(updated) => updateProvider(i, updated)}
                  onCancel={() => setEditingIdx(null)}
                  onOAuthConnected={async () => { setConfig(await llmApi.getConfig()); setEditingIdx(null) }} />
              : <ProviderCard key={i} provider={p}
                  onEdit={() => setEditingIdx(i)}
                  onDelete={() => deleteProvider(i)}
                  onRevokeOAuth={async () => {
                    if (!confirm(t("providers.revoke_oauth_confirm", { provider: p.name || p.id }))) return
                    await llmApi.oauthRevoke(p.id)
                    setConfig(await llmApi.getConfig())
                  }} />
          ))}
          {showAdd && <ProviderForm onSave={addProvider} onCancel={() => setShowAdd(false)}
            onOAuthConnected={async () => { setConfig(await llmApi.getConfig()); setShowAdd(false) }} />}
        </div>

        <DefaultModelsSection config={config} onSaved={reloadConfig} />

        <div className="flex items-center gap-3">
          <CockpitButton tone="primary" onClick={testConnection} disabled={testing || !config.default_model}>
            {testing ? <Loader2 size={14} className="mr-1 inline animate-spin" /> : <Zap size={14} className="mr-1 inline" />}
            {t("test.button")}
          </CockpitButton>
          {saving && <span className="text-xs text-[#8d9ab0]">{t("test.saving")}</span>}
          {testResult && (
            <span className={`flex items-center gap-1.5 text-sm ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}>
              {testResult.ok ? <CheckCircle size={15} /> : <XCircle size={15} />}
              {testResult.ok ? t("test.ok", { response: testResult.msg }) : testResult.msg}
            </span>
          )}
        </div>
      </div>
    </AdminOverlay>
  )
}
