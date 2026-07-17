import { Pencil } from "lucide-react"
import type { AgentBrief } from "@/features/chat/types"

interface Props {
  agents: AgentBrief[]
  projectAgentId?: string | null
  specialistAgentIds?: string[]
  selectedAgentId?: string | null
  onSelect: (agentId: string) => void
  onEdit?: (agentId: string) => void
}

export function ProjectAgentsPanel({ agents, projectAgentId, specialistAgentIds = [], selectedAgentId, onSelect, onEdit }: Props) {
  const teamIds = [projectAgentId, ...specialistAgentIds].filter((id): id is string => Boolean(id))
  const shown = [...new Set(teamIds)]
    .map((id) => agents.find((agent) => agent.id === id))
    .filter((agent): agent is AgentBrief => Boolean(agent))

  return shown.length === 0 ? (
    <p className="text-sm text-[#8d9ab0]">Keine Agenten oder Spezialisten gefunden.</p>
  ) : (
    <div className="space-y-1.5">
      {shown.map((agent) => {
        const selected = agent.id === selectedAgentId
        const isLead = agent.id === projectAgentId
        return (
          <div
            key={agent.id}
            className={[
              "flex items-center gap-1 rounded-[4px] border bg-[#111827] p-1 transition-colors",
              selected ? "border-[#69d7ff]/50 bg-[#1c2940]" : "border-[#2a364b] hover:border-[#46617f]",
            ].join(" ")}
          >
            <button
              onClick={() => onSelect(agent.id)}
              className={["min-w-0 flex-1 px-1.5 py-1 text-left text-sm font-semibold leading-none", selected ? "text-[#69d7ff]" : "text-[#e8eef8]"].join(" ")}
            >
              <span className="flex items-center gap-1.5">
                <span className="truncate">{agent.name}</span>
                <span className="shrink-0 rounded-[3px] border border-[#2a364b] px-1 py-0.5 text-[8px] font-bold uppercase tracking-wide text-[#8d9ab0]">
                  {isLead ? "Lead" : "Spezialist"}
                </span>
              </span>
              <span className="mt-1 block truncate font-mono text-[10px] font-normal text-[#8d9ab0]">{agent.llm_model || "Kein Modell zugewiesen"}</span>
            </button>
            {onEdit ? (
              <button
                onClick={() => onEdit(agent.id)}
                className="rounded-[4px] p-1.5 text-[#8d9ab0] hover:bg-white/[8%] hover:text-[#e8eef8]"
                title={`${isLead ? "Projekt-Agent" : "Spezialist"} bearbeiten`}
              >
                <Pencil size={13} />
              </button>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
