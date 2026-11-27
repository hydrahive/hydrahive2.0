import { useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import {
  BrainCircuit,
  Clock,
  Cpu,
  FileText,
  LayoutGrid,
  Mail,
  SlidersHorizontal,
  Sparkles,
  Wrench,
} from "lucide-react"
import { CompactionSection } from "@/features/agents/CompactionSection"
import { MailTab } from "@/features/agents/_MailTab"
import { ModelTab } from "@/features/agents/_ModelTab"
import { OverviewTab } from "@/features/agents/_OverviewTab"
import { PromptTab } from "@/features/agents/_PromptTab"
import { SkillsTab } from "@/features/agents/_SkillsTab"
import { SoulTab } from "@/features/agents/_SoulTab"
import { activeTabFor, isManaged, visibleTabs } from "@/features/agents/managedAgent"
import { AreasTab } from "@/features/agents/areas/AreasTab"
import type { McpServerBrief } from "@/features/agents/api"
import type { Agent, ToolMeta } from "@/features/agents/types"
import type { RegistryModel } from "@/features/llm/api"
import { ScheduledTasksPanel } from "@/features/scheduledTasks/ScheduledTasksPanel"

interface Props {
  agent: Agent
  draft: Agent
  prompt: string
  models: string[]
  catalog: RegistryModel[]
  tools: ToolMeta[]
  mcpServers: McpServerBrief[]
  onChange: (patch: Partial<Agent>) => void
  onPromptChange: (prompt: string) => void
  soulActive: boolean
  onSoulSaved: () => void
  /** Start-Reiter (Standard: Übersicht). */
  initialTab?: string
}

interface TabDefinition {
  id: string
  label: string
  icon: ComponentType<{ size?: number }>
}

export function ProjectAgentEditorTabs({
  agent,
  draft,
  prompt,
  models,
  catalog,
  tools,
  mcpServers,
  onChange,
  onPromptChange,
  soulActive,
  onSoulSaved,
  initialTab = "overview",
}: Props) {
  const { t } = useTranslation("agents")
  const [tab, setTab] = useState(initialTab)
  const hasMail = draft.tools.includes("send_mail") || draft.tools.includes("read_mail")
  const allTabs: TabDefinition[] = [
    { id: "overview", label: "Übersicht", icon: LayoutGrid },
    { id: "model", label: "Modell", icon: Cpu },
    { id: "prompt", label: t("fields.system_prompt"), icon: FileText },
    { id: "tools", label: t("tabs.tools"), icon: Wrench },
    ...(hasMail ? [{ id: "mail", label: "Mail", icon: Mail }] : []),
    { id: "skills", label: "Skills", icon: Sparkles },
    { id: "soul", label: t("tabs.soul"), icon: BrainCircuit },
    { id: "advanced", label: "Erweitert", icon: SlidersHorizontal },
    { id: "schedules", label: "Intervalle", icon: Clock },
  ]
  const tabs = visibleTabs(allTabs, agent)          // verwaltete Agenten: nur Übersicht, Modell, Intervalle

  const activeTab = activeTabFor(tab, tabs, hasMail)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <nav className="flex shrink-0 flex-wrap gap-1 border-b border-s-rand bg-s-tief px-4 pt-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 rounded-t-[4px] border-b-2 px-3 py-2 text-xs font-semibold transition-colors ${
              activeTab === id
                ? "border-[#69d7ff] bg-[#69d7ff]/10 text-[#c8f2ff]"
                : "border-transparent text-[#9aa7bc] hover:bg-white/[4%] hover:text-[#e8eef8]"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </nav>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-4xl">
          {isManaged(agent) && (
            <p className="mb-3 rounded-[4px] border border-sky-500/30 bg-sky-500/[6%] px-3 py-2 text-xs text-sky-200" data-agent-managed>
              {t("managed.hint", { module: agent.managed_by })}
            </p>
          )}
          {activeTab === "overview" && (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name">
                  <input
                    value={draft.name}
                    onChange={(event) => onChange({ name: event.target.value })}
                    className={controlClass}
                  />
                </Field>
                <Field label="Status">
                  <select
                    value={draft.status}
                    onChange={(event) => onChange({ status: event.target.value as Agent["status"] })}
                    className={controlClass}
                  >
                    <option value="active">aktiv</option>
                    <option value="disabled">deaktiviert</option>
                  </select>
                </Field>
              </div>
              <OverviewTab draft={draft} onChange={onChange} />
            </div>
          )}
          {activeTab === "model" && (
            // Modell, Fallback, Denktiefe und Budget kommen nur aus dem Agenten-Template (Aufräumen 14.11.2026).
            // Früher stand hier ein freies Feld „Thinking-Tiefe“ – Speichern scheiterte dann an agent_bound_to_template.
            <ModelTab draft={draft} catalog={catalog} onChange={onChange} />
          )}
          {activeTab === "prompt" && <PromptTab prompt={prompt} onChange={onPromptChange} soulActive={soulActive} />}
          {activeTab === "tools" && (
            <AreasTab draft={draft} tools={tools} mcpServers={mcpServers} onChange={onChange} />
          )}
          {activeTab === "mail" && hasMail && <MailTab draft={draft} onChange={onChange} />}
          {activeTab === "skills" && <SkillsTab agent={agent} draft={draft} onChange={onChange} />}
          {activeTab === "soul" && <SoulTab agent={agent} onSaved={onSoulSaved} />}
          {activeTab === "advanced" && (
            <CompactionSection agent={draft} models={models} onChange={onChange} />
          )}
          {activeTab === "schedules" && <ScheduledTasksPanel targetType="agent" targetId={agent.id} projectId={agent.project_id} />}
        </div>
      </div>
    </div>
  )
}

const controlClass = "w-full rounded-[4px] border border-s-rand bg-s-tief px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60 disabled:opacity-50"

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold text-[#9aa7bc]">{label}</label>
      {children}
    </div>
  )
}
