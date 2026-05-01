import { Save, Trash2, Loader2, Crown, User, Wrench } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { agentsApi, mcpInfoApi, type McpServerBrief } from "./api"
import { CompactionSection } from "./CompactionSection"
import { OverviewTab } from "./_OverviewTab"
import { ModelTab } from "./_ModelTab"
import { ToolsTab } from "./_ToolsTab"
import { PromptTab } from "./_PromptTab"
import { SkillsTab } from "./_SkillsTab"
import type { Agent, ToolMeta } from "./types"

interface Props {
  agent: Agent
  models: string[]
  tools: ToolMeta[]
  onSaved: (a: Agent) => void
  onDeleted: () => void
}

const TYPE_ICON = { master: Crown, project: User, specialist: Wrench }

type TabId = "overview" | "model" | "tools" | "skills" | "prompt" | "advanced"

export function AgentForm({ agent, models, tools, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(agent)
  const [prompt, setPrompt] = useState("")
  const [originalPrompt, setOriginalPrompt] = useState("")
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabId>("overview")

  useEffect(() => {
    setDraft(agent)
    setError(null)
    setTab("overview")
    agentsApi.getSystemPrompt(agent.id).then((r) => {
      setPrompt(r.prompt)
      setOriginalPrompt(r.prompt)
    })
  }, [agent.id])

  useEffect(() => {
    mcpInfoApi.list().then(setMcpServers).catch(() => {})
  }, [])

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(agent) || prompt !== originalPrompt,
    [draft, agent, prompt, originalPrompt],
  )
  const Icon = TYPE_ICON[agent.type] ?? Wrench

  function patch(p: Partial<Agent>) { setDraft((d) => ({ ...d, ...p })) }

  async function save() {
    setSaving(true); setError(null)
    try {
      const { id: _id, type: _type, created_at: _ca, updated_at: _ua, created_by: _cb, ...rest } = draft
      void _id; void _type; void _ca; void _ua; void _cb
      const updated = await agentsApi.update(agent.id, rest)
      if (prompt !== originalPrompt) {
        await agentsApi.setSystemPrompt(agent.id, prompt)
        setOriginalPrompt(prompt)
      }
      onSaved(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("errors.save_failed"))
    } finally { setSaving(false) }
  }

  async function remove() {
    if (!confirm(t("errors.delete_confirm", { name: agent.name }))) return
    await agentsApi.delete(agent.id)
    onDeleted()
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: t("tabs.overview") },
    { id: "model", label: t("tabs.model") },
    { id: "tools", label: t("tabs.tools") },
    { id: "skills", label: t("tabs.skills") },
    { id: "prompt", label: t("tabs.prompt") },
    { id: "advanced", label: t("tabs.advanced") },
  ]

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-2.5 border-b border-white/[6%] flex items-center gap-3 bg-zinc-950/80 backdrop-blur">
        <Icon size={16} className="text-violet-300 flex-shrink-0" />
        <input
          value={draft.name}
          onChange={(e) => patch({ name: e.target.value })}
          className="flex-1 bg-transparent text-base font-bold text-white focus:outline-none min-w-0"
        />
        <select
          value={draft.status}
          onChange={(e) => patch({ status: e.target.value as Agent["status"] })}
          className="px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-300"
        >
          <option value="active">{tCommon("status.active")}</option>
          <option value="disabled">{tCommon("status.disabled")}</option>
        </select>
        <button
          onClick={remove}
          className="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
          title={tCommon("actions.delete")}
        >
          <Trash2 size={14} />
        </button>
      </div>

      <div className="flex gap-1 px-5 pt-2 pb-0 border-b border-white/[6%] bg-zinc-950/60">
        {tabs.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={`px-3 py-1.5 text-xs font-medium rounded-t-md transition-colors border-b-2 -mb-px ${
              tab === tb.id
                ? "text-violet-300 border-violet-500"
                : "text-zinc-500 border-transparent hover:text-zinc-300"
            }`}
          >
            {tb.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {error && (
          <div className="mb-3 rounded-md border border-rose-500/30 bg-rose-500/[6%] px-3 py-1.5 text-xs text-rose-300">
            {error}
          </div>
        )}
        {tab === "overview" && <OverviewTab draft={draft} onChange={patch} />}
        {tab === "model" && <ModelTab draft={draft} models={models} onChange={patch} />}
        {tab === "tools" && <ToolsTab draft={draft} tools={tools} mcpServers={mcpServers} onChange={patch} />}
        {tab === "skills" && <SkillsTab agent={agent} draft={draft} onChange={patch} />}
        {tab === "prompt" && <PromptTab prompt={prompt} onChange={setPrompt} />}
        {tab === "advanced" && (
          <CompactionSection agent={draft} models={models} onChange={patch} />
        )}
      </div>

      {dirty && (
        <div className="px-5 py-2.5 border-t border-violet-500/20 bg-gradient-to-r from-violet-950/40 to-indigo-950/40 backdrop-blur flex items-center gap-3">
          <span className="text-xs text-violet-200 flex-1">
            {t("unsaved_hint")}
          </span>
          <button
            onClick={() => { setDraft(agent); setPrompt(originalPrompt) }}
            disabled={saving}
            className="px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%] transition-colors disabled:opacity-30"
          >
            {tCommon("actions.cancel")}
          </button>
          <button
            onClick={save} disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30 transition-all shadow shadow-violet-900/30"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            {tCommon("actions.save")}
          </button>
        </div>
      )}
    </div>
  )
}
