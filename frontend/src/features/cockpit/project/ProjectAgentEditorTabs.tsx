import { useState, type ComponentType } from "react"
import {
  BrainCircuit,
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
import { ToolsTab } from "@/features/agents/_ToolsTab"
import type { McpServerBrief } from "@/features/agents/api"
import type { Agent, ToolMeta } from "@/features/agents/types"
import type { RegistryModel } from "@/features/llm/api"
import { useEffortLevels } from "@/features/llm/effort"

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
}: Props) {
  const [tab, setTab] = useState("overview")
  const effortLevels = useEffortLevels(draft.llm_model)
  const hasMail = draft.tools.includes("send_mail") || draft.tools.includes("read_mail")
  const tabs: TabDefinition[] = [
    { id: "overview", label: "Übersicht", icon: LayoutGrid },
    { id: "model", label: "Modell", icon: Cpu },
    { id: "prompt", label: "Prompt", icon: FileText },
    { id: "tools", label: "Tools", icon: Wrench },
    ...(hasMail ? [{ id: "mail", label: "Mail", icon: Mail }] : []),
    { id: "skills", label: "Skills", icon: Sparkles },
    { id: "soul", label: "MD-Dateien", icon: BrainCircuit },
    { id: "advanced", label: "Erweitert", icon: SlidersHorizontal },
  ]

  const activeTab = !hasMail && tab === "mail" ? "overview" : tab

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <nav className="flex shrink-0 flex-wrap gap-1 border-b border-[#2a364b] bg-[#0b111c] px-4 pt-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 rounded-t-[4px] border-b-2 px-3 py-2 text-xs font-semibold transition-colors ${
              activeTab === id
                ? "border-[#69d7ff] bg-[#69d7ff]/10 text-[#c8f2ff]"
                : "border-transparent text-[#8d9ab0] hover:bg-white/[4%] hover:text-[#e8eef8]"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </nav>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-4xl">
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
            <div className="space-y-4">
              <ModelTab
                draft={draft}
                models={models}
                catalog={catalog}
                onChange={(patch) => onChange(patch.llm_model ? { ...patch, reasoning_effort: "" } : patch)}
              />
              <Field label="Thinking-Tiefe">
                <select
                  value={draft.reasoning_effort ?? ""}
                  disabled={effortLevels.length === 0}
                  onChange={(event) => onChange({ reasoning_effort: event.target.value })}
                  className={controlClass}
                >
                  <option value="">Modellstandard</option>
                  {effortLevels.map((level) => <option key={level} value={level}>{effortLabel(level)}</option>)}
                </select>
                <p className="mt-1 text-[11px] text-[#8d9ab0]">Standard für den Agenten; eine Session-Auswahl hat Vorrang.</p>
              </Field>
            </div>
          )}
          {activeTab === "prompt" && <PromptTab prompt={prompt} onChange={onPromptChange} />}
          {activeTab === "tools" && (
            <ToolsTab draft={draft} tools={tools} mcpServers={mcpServers} onChange={onChange} />
          )}
          {activeTab === "mail" && hasMail && <MailTab draft={draft} onChange={onChange} />}
          {activeTab === "skills" && <SkillsTab agent={agent} draft={draft} onChange={onChange} />}
          {activeTab === "soul" && <SoulTab agent={agent} />}
          {activeTab === "advanced" && (
            <CompactionSection agent={draft} models={models} onChange={onChange} />
          )}
        </div>
      </div>
    </div>
  )
}

const controlClass = "w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60 disabled:opacity-50"

function effortLabel(level: string) {
  return ({ low: "Low", medium: "Medium", high: "High", xhigh: "Extra High", max: "Max", ultra: "Ultra" } as Record<string, string>)[level] ?? level
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold text-[#8d9ab0]">{label}</label>
      {children}
    </div>
  )
}
