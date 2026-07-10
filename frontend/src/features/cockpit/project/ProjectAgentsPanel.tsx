import type { AgentBrief } from "@/features/chat/types"

interface Props {
  agents: AgentBrief[]
  projectAgentId?: string | null
  selectedAgentId?: string | null
  onSelect: (agentId: string) => void
}

export function ProjectAgentsPanel({ agents, projectAgentId, selectedAgentId, onSelect }: Props) {
  const shown = projectAgentId ? agents.filter((agent) => agent.id === projectAgentId) : []

  return shown.length === 0 ? (
    <p className="text-sm text-[#8d9ab0]">Keine Agenten gefunden.</p>
  ) : (
    <div className="space-y-1.5">
      {shown.map((agent) => {
        const selected = agent.id === selectedAgentId
        return (
          <button
            key={agent.id}
            onClick={() => onSelect(agent.id)}
            className={[
              "block w-full rounded-[4px] border px-2.5 py-2 text-left text-sm font-semibold leading-none transition-colors",
              selected
                ? "border-[#69d7ff]/50 bg-[#1c2940] text-[#69d7ff]"
                : "border-[#2a364b] bg-[#111827] text-[#e8eef8] hover:border-[#46617f] hover:bg-[#172133]",
            ].join(" ")}
          >
            <span className="block truncate">{agent.name}</span>
          </button>
        )
      })}
    </div>
  )
}
