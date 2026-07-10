import type { AgentBrief } from "@/features/chat/types"
import { CockpitPanel } from "../CockpitPanel"

interface Props {
  agents: AgentBrief[]
  projectAgentId?: string | null
}

export function ProjectAgentsPanel({ agents, projectAgentId }: Props) {
  const projectAgents = agents.filter((agent) => agent.type === "project" || agent.id === projectAgentId)
  const shown = projectAgents.length > 0 ? projectAgents : agents.filter((agent) => !agent.is_buddy).slice(0, 8)

  return (
    <CockpitPanel title="Projekt-Agenten" eyebrow="Agenten" className="min-h-[160px]">
      {shown.length === 0 ? (
        <p className="text-sm text-zinc-600">Keine Agenten gefunden.</p>
      ) : (
        <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
          {shown.map((agent) => (
            <button
              key={agent.id}
              className="block w-full rounded-[4px] border border-white/[8%] bg-white/[3%] px-2.5 py-2 text-left text-sm font-semibold text-zinc-200 hover:border-cyan-400/30 hover:bg-cyan-400/[6%]"
            >
              {agent.name}
            </button>
          ))}
        </div>
      )}
    </CockpitPanel>
  )
}
