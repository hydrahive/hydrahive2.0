import type { CSSProperties } from "react"
import { useState } from "react"
import { CheckCircle, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import type { LlmProvider } from "./api"
import { EMPTY_PROVIDER, KNOWN_PROVIDERS } from "./_llm_providers"
import { OAuthFlow } from "./OAuthFlow"

export interface ProviderFormProps {
  existing?: LlmProvider
  onSave: (p: LlmProvider) => void
  onCancel?: () => void
  onOAuthConnected?: () => void
}

export function ProviderForm({ existing, onSave, onCancel, onOAuthConnected }: ProviderFormProps) {
  const { t } = useTranslation("llm")
  const { t: tCommon } = useTranslation("common")
  const isEdit = !!existing

  const [form, setForm] = useState<LlmProvider>(existing ? { ...existing } : { ...EMPTY_PROVIDER })
  const [customModels, setCustomModels] = useState(existing ? existing.models.join(", ") : "")
  const known = KNOWN_PROVIDERS.find((p) => p.id === form.id)
  const isOAuth = (known as { auth?: string } | undefined)?.auth === "oauth"
  // Hybrid-Provider (Anthropic): Key-Feld bleibt sichtbar UND zusätzlich OAuth-Login.
  const isOAuthOptional = (known as { oauthOptional?: boolean } | undefined)?.oauthOptional === true
  const hasToken = !!form.oauth?.access

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const models = customModels.split(",").map((s) => s.trim()).filter(Boolean)
    onSave({ ...form, name: form.name || known?.name || form.id, models })
    if (!isEdit) { setForm({ ...EMPTY_PROVIDER }); setCustomModels("") }
  }

  return (
    <form onSubmit={handleSubmit} className="box overflow-hidden p-4 space-y-3" style={{ "--c": rgbFor("/llm") } as CSSProperties}>
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{isEdit ? form.name || form.id : t("providers.add")}</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-zinc-500 mb-1">{t("form.provider_label")}</label>
          <select value={form.id} disabled={isEdit}
            onChange={(e) => { setForm({ ...form, id: e.target.value, name: KNOWN_PROVIDERS.find(p => p.id === e.target.value)?.name ?? "" }) }}
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
          {isOAuth ? (
            <div className="px-3 py-2 rounded-lg bg-white/[3%] border border-white/[6%] text-xs text-zinc-500 italic">
              {hasToken
                ? <span className="flex items-center gap-1.5 text-emerald-400 not-italic"><CheckCircle size={12} /> Verbunden</span>
                : known?.placeholder ?? "OAuth — kein Key"}
            </div>
          ) : (
            <input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              placeholder={known?.placeholder ?? t("form.api_key")}
              className="w-full px-3 py-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
          )}
        </div>
      </div>
      {form.id === "minimax" && (
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Group ID <span className="text-zinc-600">(MiniMax)</span></label>
          <input type="text" value={form.group_id ?? ""} onChange={(e) => setForm({ ...form, group_id: e.target.value || undefined })}
            placeholder="z.B. 123456789"
            className="w-full px-3 py-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
        </div>
      )}
      {isOAuth && !hasToken && (
        <OAuthFlow
          providerId={form.id}
          onConnected={() => onOAuthConnected?.()}
        />
      )}
      {isOAuthOptional && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[11px] text-zinc-500">
            <span className="h-px flex-1 bg-white/[8%]" />
            {t("form.or_oauth")}
            <span className="h-px flex-1 bg-white/[8%]" />
          </div>
          {hasToken ? (
            <p className="flex items-center gap-1.5 text-xs text-emerald-400">
              <CheckCircle size={12} /> {t("form.oauth_connected")}
            </p>
          ) : (
            <OAuthFlow
              providerId={form.id}
              onConnected={() => onOAuthConnected?.()}
            />
          )}
        </div>
      )}
      {known && (
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Eigene Modelle (optional, kommagetrennt)</label>
          <input type="text" value={customModels} onChange={(e) => setCustomModels(e.target.value)}
            placeholder="z.B. openrouter/deepseek/deepseek-v4-flash:free"
            className="w-full px-3 py-2 rounded-lg bg-white/[3%] border border-white/[6%] text-zinc-300 text-xs font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/40" />
          <p className="text-[10px] text-zinc-500 mt-1">Live-Modelle des Providers erscheinen automatisch. Hier nur Modelle ergänzen, die nicht in der Live-Liste sind.</p>
        </div>
      )}
      <div className="flex items-center gap-2">
        <button type="submit"
          disabled={
            !form.id
            || (isOAuth && !hasToken)
            // Hybrid (Anthropic): Key ODER OAuth-Token reicht.
            || (isOAuthOptional && !form.api_key && !hasToken)
            || (!isOAuth && !isOAuthOptional && !form.api_key)
          }
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
