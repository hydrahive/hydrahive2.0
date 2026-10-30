import { Loader2, Pencil, SquarePen } from "lucide-react"
import type { AgentBrief } from "@/features/chat/types"

interface Props {
  agents: AgentBrief[]
  projectAgentId?: string | null
  specialistAgentIds?: string[]
  selectedAgentId?: string | null
  onSelect: (agentId: string) => void
  onEdit?: (agentId: string) => void
  /** Startet eine neue Projekt-Session mit GENAU diesem Agenten (inkl. Übergabe). */
  onNewSession?: (agentId: string) => void
  /** Agent-ID, für die gerade eine Session erstellt wird (Übergabe läuft). */
  newSessionAgentId?: string | null
}

export function ProjectAgentsPanel({ agents, projectAgentId, specialistAgentIds = [], selectedAgentId, onSelect, onEdit, onNewSession, newSessionAgentId = null }: Props) {
  const teamIds = [projectAgentId, ...specialistAgentIds].filter((id): id is string => Boolean(id))
  const shown = [...new Set(teamIds)]
    .map((id) => agents.find((agent) => agent.id === id))
    .filter((agent): agent is AgentBrief => Boolean(agent))

  return shown.length === 0 ? (
    <p className="text-sm text-[#9aa7bc]">Keine Agenten oder Spezialisten gefunden.</p>
  ) : (
    <div className="space-y-1.5">
      {shown.map((agent) => {
        const selected = agent.id === selectedAgentId
        const isLead = agent.id === projectAgentId
        // Während einer laufenden Übergabe alle Aktionen sperren — sonst
        // entstehen bei Doppelklick zwei Sessions bzw. zwei Handover-Läufe.
        const busy = newSessionAgentId !== null
        const busyHere = newSessionAgentId === agent.id
        return (
          <div
            key={agent.id}
            className={[
              "flex items-center gap-1 rounded-[4px] border bg-s-innen p-1 transition-colors",
              selected ? "border-[#69d7ff]/50 bg-[#1c2940]" : "border-s-rand hover:border-s-rand-hover",
            ].join(" ")}
          >
            <button
              onClick={() => onSelect(agent.id)}
              disabled={busy}
              className={["min-w-0 flex-1 px-1.5 py-1 text-left text-sm font-semibold leading-none disabled:cursor-not-allowed", selected ? "text-[#69d7ff]" : "text-[#e8eef8]"].join(" ")}
            >
              <span className="flex items-center gap-1.5">
                <span className="truncate">{agent.name}</span>
                <span className="shrink-0 rounded-[3px] border border-s-rand px-1 py-0.5 text-[8px] font-bold uppercase tracking-wide text-[#9aa7bc]">
                  {isLead ? "Lead" : "Spezialist"}
                </span>
              </span>
              <span className="mt-1 block truncate font-mono text-[10px] font-normal text-[#9aa7bc]">{agent.llm_model || "Kein Modell zugewiesen"}</span>
            </button>
            {onNewSession ? (
              <button
                onClick={() => onNewSession(agent.id)}
                disabled={busy}
                className="rounded-[4px] p-1.5 text-[#9aa7bc] transition-colors hover:bg-white/[8%] hover:text-[#69d7ff] disabled:cursor-not-allowed disabled:opacity-40"
                title={`Neue Session mit ${agent.name} starten (bisherige Session wird übergeben)`}
              >
                {busyHere ? <Loader2 size={13} className="animate-spin" /> : <SquarePen size={13} />}
              </button>
            ) : null}
            {onEdit ? (
              <button
                onClick={() => onEdit(agent.id)}
                disabled={busy}
                className="rounded-[4px] p-1.5 text-[#9aa7bc] hover:bg-white/[8%] hover:text-[#e8eef8] disabled:cursor-not-allowed disabled:opacity-40"
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
