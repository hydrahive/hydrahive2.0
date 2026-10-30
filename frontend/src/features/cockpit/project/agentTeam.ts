import type { AgentBrief } from "@/features/chat/types"

/** Projekt-Team: Lead zuerst, dann die Spezialisten; doppelte und unbekannte IDs fallen raus. */
export function teamList(agents: AgentBrief[], leadId: string | null | undefined, specialistIds: string[] = []): AgentBrief[] {
  const ids = [...new Set([leadId, ...specialistIds].filter((id): id is string => Boolean(id)))]
  return ids.map((id) => agents.find((agent) => agent.id === id)).filter((agent): agent is AgentBrief => Boolean(agent))
}

interface Options {
  selectedId?: string | null
  expanded: boolean
  query: string
  limit: number
}

/**
 * Sichtbarer Teil des Teams (Plan projekt-cockpit-kompakt): eingeklappt höchstens `limit`, der gewählte Agent ist immer
 * dabei. Mit Suche alle Treffer (Name oder Modell).
 */
export function visibleTeam(team: AgentBrief[], { selectedId, expanded, query, limit }: Options): { shown: AgentBrief[]; hidden: number } {
  const q = query.trim().toLowerCase()
  if (q) {
    const treffer = team.filter((a) => a.name.toLowerCase().includes(q) || (a.llm_model ?? "").toLowerCase().includes(q))
    return { shown: treffer, hidden: 0 }
  }
  if (expanded || team.length <= limit) return { shown: team, hidden: 0 }
  let shown = team.slice(0, limit)
  const selected = team.find((a) => a.id === selectedId)
  if (selected && !shown.includes(selected)) shown = [...shown.slice(0, limit - 1), selected]
  return { shown, hidden: team.length - shown.length }
}
