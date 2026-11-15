import type { AgentBrief } from "@/features/chat/types"

/**
 * Projekt-Team: Lead immer zuerst, dann aktive Spezialisten, dann deaktivierte Spezialisten
 * ans Ende; doppelte und unbekannte IDs fallen raus.
 *
 * Deaktivierte Spezialisten wurden zunächst ganz ausgefiltert (#722) — das Problem war damit
 * nur verschoben: genau die Agenten, die man wegräumen will, waren unsichtbar (Till 15.11.).
 * Jetzt bleiben sie sichtbar (ausgegraut, ans Ende sortiert, siehe ProjectAgentsPanel), damit
 * man sie mit 1–2 Klicks (Papierkorb-Symbol) direkt löschen/archivieren kann.
 */
export function teamList(agents: AgentBrief[], leadId: string | null | undefined, specialistIds: string[] = []): AgentBrief[] {
  const ids = [...new Set([leadId, ...specialistIds].filter((id): id is string => Boolean(id)))]
  const found = ids.map((id) => agents.find((agent) => agent.id === id)).filter((agent): agent is AgentBrief => Boolean(agent))
  const rank = (agent: AgentBrief) => (agent.id === leadId ? 0 : agent.status === "disabled" ? 2 : 1)
  return [...found].sort((a, b) => rank(a) - rank(b))
}

/** Nur die wählbaren Teammitglieder: der Lead (unabhängig vom Status) und aktive Spezialisten.
 *  Ein deaktivierter Spezialist kann laut Runner nicht laufen und darf daher nicht als
 *  selectedAgentId stehen bleiben, auch wenn er jetzt sichtbar in der Liste steht. */
export function selectableTeamIds(agents: AgentBrief[], leadId: string | null | undefined, specialistIds: string[] = []): Set<string> {
  const team = teamList(agents, leadId, specialistIds)
  return new Set(team.filter((agent) => agent.id === leadId || agent.status !== "disabled").map((agent) => agent.id))
}

interface SplitTeamResult {
  /** Lead + aktive Spezialisten — unterliegen dem normalen Limit/der Suche. */
  active: AgentBrief[]
  /** Deaktivierte Spezialisten (nie der Lead) — eigene, einklappbare Gruppe. */
  disabled: AgentBrief[]
}

/**
 * Trennt das sortierte Team (teamList) in einen normalen und einen deaktivierten Teil.
 *
 * Grund: Zählt man deaktivierte Spezialisten ins normale LIMIT/die Suche mit, verschwinden
 * sie bei vielen alten Spezialisten (z.B. 10 im DEV-Projekt) hinter „Alle anzeigen“ — ein
 * unnötiger Extra-Klick, genau für die Agenten, die man wegräumen will (Review zu PR #724).
 * Der deaktivierte Teil bekommt stattdessen eine eigene, einklappbare Gruppe
 * (ProjectAgentDisabledGroup) ohne Limit: einmal aufklappen, dann ist jeder mit Papierkorb +
 * „Ins Archiv starten" in 2 Klicks erreichbar.
 */
export function splitTeam(team: AgentBrief[], leadId: string | null | undefined): SplitTeamResult {
  const active: AgentBrief[] = []
  const disabled: AgentBrief[] = []
  for (const agent of team) {
    if (agent.id === leadId || agent.status !== "disabled") active.push(agent)
    else disabled.push(agent)
  }
  return { active, disabled }
}

interface AgentDeletedResult {
  agents: AgentBrief[]
  /** Neue Auswahl für selectedAgentId — unverändert, außer der gelöschte Agent war gewählt. */
  selectedAgentId: string | null
}

/**
 * Reine Logik für „Spezialist gelöscht“ (ProjectCockpitPage): aus der Agenten-Liste
 * entfernen und — falls er gerade ausgewählt war — die Auswahl auf den Projekt-Agenten
 * zurückfallen lassen. Ausgelagert, damit der Rückfall ohne Overlay/State getestet werden kann.
 */
export function removeAgentFromTeam(
  agents: AgentBrief[],
  deletedAgentId: string,
  selectedAgentId: string | null,
  projectAgentId: string | null,
): AgentDeletedResult {
  return {
    agents: agents.filter((agent) => agent.id !== deletedAgentId),
    selectedAgentId: selectedAgentId === deletedAgentId ? projectAgentId : selectedAgentId,
  }
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
