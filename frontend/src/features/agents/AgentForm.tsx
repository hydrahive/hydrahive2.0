import { Save, Loader2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { agentsApi, mcpInfoApi, type McpServerBrief } from "./api"
import { CompactionSection } from "./CompactionSection"
import { OverviewTab } from "./_OverviewTab"
import { ModelTab } from "./_ModelTab"
import { ToolsTab } from "./_ToolsTab"
import { SoulTab } from "./_SoulTab"
import { SkillsTab } from "./_SkillsTab"
import { AgentFormHeader } from "./_AgentFormHeader"
import { AgentTabBar } from "./_AgentTabBar"
import type { Agent, ToolMeta } from "./types"

interface Props {
  agent: Agent
  models: string[]
  tools: ToolMeta[]
  onSaved: (a: Agent) => void
  onDeleted: () => void
}

type TabId = "overview" | "model" | "tools" | "skills" | "soul" | "advanced"

export function AgentForm({ agent, models, tools, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(agent)
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabId>("overview")

  useEffect(() => {
    setDraft(agent); setError(null); setTab("overview")
  }, [agent.id])

  useEffect(() => {
    mcpInfoApi.list().then(setMcpServers).catch(() => {})
  }, [])

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(agent),
    [draft, agent],
  )

  function patch(p: Partial<Agent>) { setDraft((d) => ({ ...d, ...p })) }

  async function save() {
    setSaving(true); setError(null)
    try {
      const { id: _id, type: _type, created_at: _ca, updated_at: _ua, created_by: _cb, ...rest } = draft
      void _id; void _type; void _ca; void _ua; void _cb
      const updated = await agentsApi.update(agent.id, rest)
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
    { id: "soul", label: t("tabs.soul") },
    { id: "advanced", label: t("tabs.advanced") },
  ]

  return (
    <div className="flex flex-col h-full">
      <AgentFormHeader
        agent={agent} draftName={draft.name} draftStatus={draft.status}
        onNameChange={(name) => patch({ name })}
        onStatusChange={(status) => patch({ status })}
        onDelete={remove}
      />
      <AgentTabBar tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)} />

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
        {tab === "soul" && <SoulTab agent={agent} />}
        {tab === "advanced" && <CompactionSection agent={draft} models={models} onChange={patch} />}
      </div>

      {dirty && (
        <div className="px-5 py-2.5 border-t border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)] backdrop-blur flex items-center gap-3">
          <span className="text-xs text-[var(--hh-accent-text)] flex-1">{t("unsaved_hint")}</span>
          <button
            onClick={() => { setDraft(agent) }}
            disabled={saving}
            className="px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%] transition-colors disabled:opacity-30"
          >
            {tCommon("actions.cancel")}
          </button>
          <button onClick={save} disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white text-xs font-medium disabled:opacity-30 transition-all shadow shadow-black/30"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            {tCommon("actions.save")}
          </button>
        </div>
      )}
    </div>
  )
}
