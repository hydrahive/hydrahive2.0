import { Pencil } from "lucide-react"
import type { AgentBrief } from "@/features/chat/types"

interface Props {
  agents: AgentBrief[]
  projectAgentId?: string | null
  selectedAgentId?: string | null
  onSelect: (agentId: string) => void
  onEdit?: (agentId: string) => void
}

export function ProjectAgentsPanel({ agents, projectAgentId, selectedAgentId, onSelect, onEdit }: Props) {
  const shown = projectAgentId ? agents.filter((agent) => agent.id === projectAgentId) : []

  return shown.length === 0 ? (
    <p className="text-sm text-[#8d9ab0]">Keine Agenten gefunden.</p>
  ) : (
    <div className="space-y-1.5">
      {shown.map((agent) => {
        const selected = agent.id === selectedAgentId
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
              <span className="block truncate">{agent.name}</span>
              <span className="mt-1 block truncate font-mono text-[10px] font-normal text-[#8d9ab0]">{agent.llm_model}</span>
            </button>
            {onEdit ? (
              <button
                onClick={() => onEdit(agent.id)}
                className="rounded-[4px] p-1.5 text-[#8d9ab0] hover:bg-white/[8%] hover:text-[#e8eef8]"
                title="Agent bearbeiten"
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
