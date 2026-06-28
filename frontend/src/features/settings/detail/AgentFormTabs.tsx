import { Save, Loader2, LayoutGrid, Cpu, Wrench, Sparkles, BrainCircuit, SlidersHorizontal, Mail } from "lucide-react"
import { useEffect, useMemo, useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import { agentsApi, mcpInfoApi, type McpServerBrief } from "@/features/agents/api"
import { CompactionSection } from "@/features/agents/CompactionSection"
import { OverviewTab } from "@/features/agents/_OverviewTab"
import { ModelTab } from "@/features/agents/_ModelTab"
import { ToolsTab } from "@/features/agents/_ToolsTab"
import { MailTab } from "@/features/agents/_MailTab"
import { SoulTab } from "@/features/agents/_SoulTab"
import { SkillsTab } from "@/features/agents/_SkillsTab"
import { AgentFormHeader } from "@/features/agents/_AgentFormHeader"
import type { Agent, ToolMeta } from "@/features/agents/types"
import type { RegistryModel } from "@/features/llm/api"

interface Props {
  agent: Agent
  models: string[]
  catalog: RegistryModel[]
  tools: ToolMeta[]
  onSaved: (a: Agent) => void
  onDeleted: () => void
}

/**
 * Agenten-Einstellungen als horizontale KARTEIKARTEN (Tills Blueprint-Schema):
 * Reiter-Leiste oben, pro Reiter EINE Seite mit voller Breite — statt der
 * gequetschten Masonry-Box-Liste der alten AgentForm. Nutzt dieselben
 * Tab-Komponenten + Save/Draft-Logik, nur anders angeordnet.
 */
export function AgentFormTabs({ agent, models, catalog, tools, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(agent)
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState("overview")

  useEffect(() => { setDraft(agent); setError(null) }, [agent.id])
  useEffect(() => { mcpInfoApi.list().then(setMcpServers).catch(() => {}) }, [])

  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(agent), [draft, agent])
  function patch(p: Partial<Agent>) { setDraft((d) => ({ ...d, ...p })) }

  async function save() {
    setSaving(true); setError(null)
    try {
      const { id: _id, type: _type, created_at: _ca, updated_at: _ua, created_by: _cb, ...rest } = draft
      void _id; void _type; void _ca; void _ua; void _cb
      onSaved(await agentsApi.update(agent.id, rest))
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

  // Reiter-Definition. icon + Label (i18n) + Inhalt.
  const TABS: { id: string; icon: ComponentType<{ size?: number }>; label: string; show?: boolean }[] = [
    { id: "overview", icon: LayoutGrid, label: t("tabs.overview") },
    { id: "model", icon: Cpu, label: t("tabs.model") },
    { id: "tools", icon: Wrench, label: t("tabs.tools") },
    { id: "mail", icon: Mail, label: t("tabs.mail"), show: hasMail },
    { id: "skills", icon: Sparkles, label: t("tabs.skills") },
    { id: "soul", icon: BrainCircuit, label: t("tabs.soul") },
    { id: "advanced", icon: SlidersHorizontal, label: t("tabs.advanced") },
  ].filter((x) => x.show !== false)

  // Falls der aktive Reiter ausgeblendet ist (z.B. Mail weg), zurück auf overview.
  useEffect(() => {
    if (!TABS.some((x) => x.id === tab)) setTab("overview")
  }, [hasMail]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-full flex-col">
      <AgentFormHeader
        agent={agent} draftName={draft.name} draftStatus={draft.status}
        onNameChange={(name) => patch({ name })}
        onStatusChange={(status) => patch({ status })}
        onDelete={remove}
      />

      {/* Karteikarten-Reiter */}
      <div className="flex flex-wrap items-center gap-1 border-b border-white/8 px-4 pt-2">
        {TABS.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm transition-colors ${
              tab === id
                ? "bg-[#104E8B]/20 text-sky-200 border-b-2 border-sky-400"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[4%]"
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Reiter-Inhalt: volle Breite, eigener Scroll */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {error && (
          <div className="mb-3 rounded-md border border-rose-500/30 bg-rose-500/[6%] px-3 py-1.5 text-xs text-rose-300">{error}</div>
        )}
        <div className="max-w-3xl">
          {tab === "overview" && <OverviewTab draft={draft} onChange={patch} />}
          {tab === "model" && <ModelTab draft={draft} models={models} catalog={catalog} onChange={patch} />}
          {tab === "tools" && <ToolsTab draft={draft} tools={tools} mcpServers={mcpServers} onChange={patch} />}
          {tab === "mail" && hasMail && <MailTab draft={draft} onChange={patch} />}
          {tab === "skills" && <SkillsTab agent={agent} draft={draft} onChange={patch} />}
          {tab === "soul" && <SoulTab agent={agent} />}
          {tab === "advanced" && <CompactionSection agent={draft} models={models} onChange={patch} />}
        </div>
      </div>

      {dirty && (
        <div className="flex items-center gap-3 border-t border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)] px-5 py-2.5 backdrop-blur">
          <span className="flex-1 text-xs text-[var(--hh-accent-text)]">{t("unsaved_hint")}</span>
          <button onClick={() => setDraft(agent)} disabled={saving}
            className="rounded-md px-3 py-1.5 text-xs text-zinc-400 hover:bg-white/[5%] hover:text-zinc-200 transition-colors disabled:opacity-30">
            {tCommon("actions.cancel")}
          </button>
          <button onClick={save} disabled={saving}
            className="flex items-center gap-1.5 rounded-md bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] px-4 py-1.5 text-xs font-medium text-white shadow shadow-black/30 transition-all hover:brightness-110 disabled:opacity-30">
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            {tCommon("actions.save")}
          </button>
        </div>
      )}
    </div>
  )
}
