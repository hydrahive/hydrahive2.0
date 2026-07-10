import type { AgentBrief } from "@/features/chat/types"
import { CockpitPanel } from "../CockpitPanel"

interface Props {
  agents: AgentBrief[]
  projectAgentId?: string | null
  selectedAgentId?: string | null
  onSelect: (agentId: string) => void
}

export function ProjectAgentsPanel({ agents, projectAgentId, selectedAgentId, onSelect }: Props) {
  const shown = projectAgentId ? agents.filter((agent) => agent.id === projectAgentId) : []

  return (
    <CockpitPanel title="Projekt-Agenten" eyebrow="Agenten" className="min-h-[160px]">
      {shown.length === 0 ? (
        <p className="text-sm text-zinc-600">Keine Agenten gefunden.</p>
      ) : (
        <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
          {shown.map((agent) => {
            const selected = agent.id === selectedAgentId
            return (
              <button
                key={agent.id}
                onClick={() => onSelect(agent.id)}
                className={[
                  "block w-full rounded-[4px] border px-2.5 py-2 text-left text-sm font-semibold leading-none transition-colors",
                  selected
                    ? "border-cyan-300/50 bg-cyan-400/10 text-cyan-100 shadow-[0_0_20px_-14px_rgba(34,211,238,0.9)]"
                    : "border-white/[8%] bg-white/[3%] text-zinc-200 hover:border-cyan-400/30 hover:bg-cyan-400/[6%]",
                ].join(" ")}
              >
                <span className="block truncate">{agent.name}</span>
              </button>
            )
          })}
        </div>
      )}
    </CockpitPanel>
  )
}
