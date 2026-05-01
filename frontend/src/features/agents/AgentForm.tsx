import { Save, Trash2, Loader2, Crown, User, Wrench } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { agentsApi, mcpInfoApi, type McpServerBrief } from "./api"
import { CompactionSection } from "./CompactionSection"
import { McpSelector } from "./McpSelector"
import { ToolsSelector } from "./ToolsSelector"
import type { Agent, ToolMeta } from "./types"

interface Props {
  agent: Agent
  models: string[]
  tools: ToolMeta[]
  onSaved: (a: Agent) => void
  onDeleted: () => void
}

const TYPE_ICON = { master: Crown, project: User, specialist: Wrench }

export function AgentForm({ agent, models, tools, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(agent)
  const [prompt, setPrompt] = useState("")
  const [originalPrompt, setOriginalPrompt] = useState("")
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(agent)
    setError(null)
    agentsApi.getSystemPrompt(agent.id).then((r) => {
      setPrompt(r.prompt)
      setOriginalPrompt(r.prompt)
    })
  }, [agent.id])

  useEffect(() => {
    mcpInfoApi.list().then(setMcpServers).catch(() => {})
  }, [])

  const dirty =
    JSON.stringify(draft) !== JSON.stringify(agent) || prompt !== originalPrompt
  const Icon = TYPE_ICON[agent.type] ?? Wrench

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const { id, type, created_at, updated_at, created_by, ...patch } = draft
      const updated = await agentsApi.update(agent.id, patch)
      if (prompt !== originalPrompt) {
        await agentsApi.setSystemPrompt(agent.id, prompt)
        setOriginalPrompt(prompt)
      }
      onSaved(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("errors.save_failed"))
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!confirm(t("errors.delete_confirm", { name: agent.name }))) return
    await agentsApi.delete(agent.id)
    onDeleted()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-2.5 border-b border-white/[6%] flex items-center gap-3">
        <Icon size={16} className="text-violet-300 flex-shrink-0" />
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          className="flex-1 bg-transparent text-base font-bold text-white focus:outline-none"
        />
        <select
          value={draft.status}
          onChange={(e) => setDraft({ ...draft, status: e.target.value as Agent["status"] })}
          className="px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-300"
        >
          <option value="active">{tCommon("status.active")}</option>
          <option value="disabled">{tCommon("status.disabled")}</option>
        </select>
        <button
          onClick={save}
          disabled={!dirty || saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow shadow-violet-900/20"
        >
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          {tCommon("actions.save")}
        </button>
        <button
          onClick={remove}
          className="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-3 space-y-3">
        {error && (
          <div className="rounded-md border border-rose-500/30 bg-rose-500/[6%] px-3 py-1.5 text-xs text-rose-300">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <Field label={t("fields.type")}>
            <p className="px-2 py-1 text-xs text-zinc-300 font-mono">{t(`type.${draft.type}`)}</p>
          </Field>
          <Field label={t("fields.model")}>
            <select
              value={draft.llm_model}
              onChange={(e) => setDraft({ ...draft, llm_model: e.target.value })}
              className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
            >
              {!models.includes(draft.llm_model) && (
                <option value={draft.llm_model}>{t("fields.model_not_in_config", { model: draft.llm_model })}</option>
              )}
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label={t("fields.temperature")}>
            <input type="number" step="0.1" min="0" max="2" value={draft.temperature}
              onChange={(e) => setDraft({ ...draft, temperature: parseFloat(e.target.value) })}
              className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
          </Field>
          <Field label={t("fields.max_tokens")}>
            <input type="number" value={draft.max_tokens}
              onChange={(e) => setDraft({ ...draft, max_tokens: parseInt(e.target.value) })}
              className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
          </Field>
        </div>

        <Field label={t("fields.fallback_models")} hint={t("fields.fallback_hint")}>
          <FallbackModelsSelector
            primary={draft.llm_model}
            available={models}
            selected={draft.fallback_models ?? []}
            onChange={(fb) => setDraft({ ...draft, fallback_models: fb })}
          />
        </Field>

        <Field label={t("fields.description")}>
          <input value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
        </Field>

        <Field label={t("fields.tools_count", { selected: draft.tools.length, total: tools.length })}>
          <ToolsSelector available={tools} selected={draft.tools}
            onChange={(t) => setDraft({ ...draft, tools: t })} />
        </Field>

        <Field label={t("fields.mcp_count", { selected: draft.mcp_servers.length, total: mcpServers.length })}>
          <McpSelector available={mcpServers} selected={draft.mcp_servers}
            onChange={(s) => setDraft({ ...draft, mcp_servers: s })} />
        </Field>

        <Field label={t("fields.system_prompt")}>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={8}
            className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
        </Field>

        <CompactionSection agent={draft} models={models}
          onChange={(patch) => setDraft({ ...draft, ...patch })} />
      </div>
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

function FallbackModelsSelector({
  primary, available, selected, onChange,
}: { primary: string; available: string[]; selected: string[]; onChange: (s: string[]) => void }) {
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
