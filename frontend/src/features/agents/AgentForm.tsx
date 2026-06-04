import { Save, Loader2, LayoutGrid, Cpu, Wrench, Sparkles, BrainCircuit, SlidersHorizontal, Mail } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { agentsApi, mcpInfoApi, type McpServerBrief } from "./api"
import { CompactionSection } from "./CompactionSection"
import { OverviewTab } from "./_OverviewTab"
import { ModelTab } from "./_ModelTab"
import { ToolsTab } from "./_ToolsTab"
import { MailTab } from "./_MailTab"
import { SoulTab } from "./_SoulTab"
import { SkillsTab } from "./_SkillsTab"
import { AgentFormHeader } from "./_AgentFormHeader"
import type { Agent, ToolMeta } from "./types"
import type { RegistryModel } from "@/features/llm/api"

interface Props {
  agent: Agent
  models: string[]
  catalog: RegistryModel[]
  tools: ToolMeta[]
  onSaved: (a: Agent) => void
  onDeleted: () => void
}

const C = rgbFor("/agents")
// Dichte Box-Klasse: kein Hover-Lift (Formular), kein Spalten-Umbruch (Masonry), Abstand.
const BOX = "box-static mb-3 break-inside-avoid"

export function AgentForm({ agent, models, catalog, tools, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(agent)
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(agent); setError(null)
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

  const hasMail = draft.tools.includes("send_mail") || draft.tools.includes("read_mail")

  return (
    <div className="flex flex-col h-full">
      <AgentFormHeader
        agent={agent} draftName={draft.name} draftStatus={draft.status}
        onNameChange={(name) => patch({ name })}
        onStatusChange={(status) => patch({ status })}
        onDelete={remove}
      />

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {error && (
          <div className="mb-3 rounded-md border border-rose-500/30 bg-rose-500/[6%] px-3 py-1.5 text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Übersicht: volle Breite, ganz oben (außerhalb des Masonry-Grids). */}
        <CollapsibleBox boxId="agent-overview" color={C} className="box-static mb-3" icon={<LayoutGrid size={14} />} title={t("tabs.overview")}>
          <div className="box-b"><OverviewTab draft={draft} onChange={patch} /></div>
        </CollapsibleBox>

        <div className="columns-1 xl:columns-2 2xl:columns-3 gap-3">
          <CollapsibleBox boxId="agent-model" color={C} className={BOX} icon={<Cpu size={14} />} title={t("tabs.model")}>
            <div className="box-b"><ModelTab draft={draft} models={models} catalog={catalog} onChange={patch} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="agent-tools" color={C} className={BOX} icon={<Wrench size={14} />} title={t("tabs.tools")}>
            <div className="box-b"><ToolsTab draft={draft} tools={tools} mcpServers={mcpServers} onChange={patch} /></div>
          </CollapsibleBox>

          {hasMail && (
            <CollapsibleBox boxId="agent-mail" color={C} className={BOX} icon={<Mail size={14} />} title={t("tabs.mail")}>
              <div className="box-b"><MailTab draft={draft} onChange={patch} /></div>
            </CollapsibleBox>
          )}

          <CollapsibleBox boxId="agent-skills" color={C} className={BOX} icon={<Sparkles size={14} />} title={t("tabs.skills")}>
            <div className="box-b"><SkillsTab agent={agent} draft={draft} onChange={patch} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="agent-soul" color={C} className={BOX} icon={<BrainCircuit size={14} />} title={t("tabs.soul")}>
            <div className="box-b"><SoulTab agent={agent} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="agent-advanced" color={C} className={BOX} icon={<SlidersHorizontal size={14} />} title={t("tabs.advanced")} defaultCollapsed>
            <div className="box-b"><CompactionSection agent={draft} models={models} onChange={patch} /></div>
          </CollapsibleBox>
        </div>
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
