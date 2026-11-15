import { useState } from "react"
import { ChevronDown, ChevronUp, Search } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { AgentBrief } from "@/features/chat/types"
import { splitTeam, teamList, visibleTeam } from "./agentTeam"
import { ProjectAgentDisabledGroup } from "./ProjectAgentDisabledGroup"
import { ProjectAgentRow } from "./ProjectAgentRow"

interface Props {
  agents: AgentBrief[]
  projectId?: string | null
  projectAgentId?: string | null
  specialistAgentIds?: string[]
  selectedAgentId?: string | null
  onSelect: (agentId: string) => void
  onEdit?: (agentId: string) => void
  /** Startet eine neue Projekt-Session mit GENAU diesem Agenten (inkl. Übergabe). */
  onNewSession?: (agentId: string) => void
  /** Agent-ID, für die gerade eine Session erstellt wird (Übergabe läuft). */
  newSessionAgentId?: string | null
  /** Spezialist wurde über das Papierkorb-Symbol gelöscht/archiviert. */
  onDeleted?: (agentId: string) => void
}

/** So viele Agenten zeigt die Liste eingeklappt (Plan projekt-cockpit-kompakt). */
const LIMIT = 4
/** Ab so vielen Agenten erscheint die Suche. */
const SUCHE_AB = 8

/**
 * Projekt-Team, eine Zeile je Agent. Modell als Tooltip; Lead und gewählter Agent zeigen es
 * auch sichtbar. Deaktivierte Spezialisten stehen NICHT in der normalen (durch LIMIT
 * begrenzten) Liste, sondern in einer eigenen, einklappbaren Gruppe darunter
 * (ProjectAgentDisabledGroup) — sonst verschwinden sie bei vielen alten Spezialisten hinter
 * „Alle anzeigen", ein unnötiger Extra-Klick für genau die Agenten, die man wegräumen will
 * (Review zu PR #724, Till 15.11.: „mit einem oder 2 Klicks fertig").
 */
export function ProjectAgentsPanel({ agents, projectId, projectAgentId, specialistAgentIds = [], selectedAgentId, onSelect, onEdit, onNewSession, newSessionAgentId = null, onDeleted }: Props) {
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [expanded, setExpanded] = useState(false)
  const [query, setQuery] = useState("")
  const team = teamList(agents, projectAgentId, specialistAgentIds)
  const { active, disabled } = splitTeam(team, projectAgentId)
  const { shown, hidden } = visibleTeam(active, { selectedId: selectedAgentId, expanded, query, limit: LIMIT })
  // Während einer laufenden Übergabe alle Aktionen sperren — sonst entstehen bei Doppelklick zwei Sessions.
  const busy = newSessionAgentId !== null

  if (team.length === 0) return <p className="text-sm text-[#9aa7bc]">Keine Agenten oder Spezialisten gefunden.</p>

  return (
    <div className="space-y-1">
      {active.length >= SUCHE_AB && (
        <label className="mb-1.5 flex items-center gap-2 rounded-[4px] border border-s-rand bg-s-tief px-2 py-1 text-xs text-[#9aa7bc]">
          <Search size={12} aria-hidden="true" />
          <span className="sr-only">Team durchsuchen</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`${active.length} Agenten durchsuchen …`}
            className="min-w-0 flex-1 bg-transparent text-[#e8eef8] outline-none placeholder:text-[#9aa7bc]" />
        </label>
      )}
      {shown.map((agent) => (
        <ProjectAgentRow key={agent.id} agent={agent} isLead={agent.id === projectAgentId} isDisabled={false}
          selected={agent.id === selectedAgentId} busy={busy} isAdmin={isAdmin} onSelect={onSelect} onEdit={onEdit}
          onNewSession={onNewSession} newSessionAgentId={newSessionAgentId} onDeleted={onDeleted} />
      ))}
      {query.trim() && shown.length === 0 && <p className="px-1 text-xs text-[#9aa7bc]">Kein Agent passt zur Suche.</p>}
      {!query.trim() && active.length > LIMIT && (
        <button type="button" onClick={() => setExpanded((e) => !e)}
          className="flex w-full items-center justify-center gap-1 rounded-[4px] px-2 py-1 text-xs font-bold text-[#69d7ff] hover:bg-s-hebung">
          {expanded ? <><ChevronUp size={12} /> Weniger anzeigen</> : <><ChevronDown size={12} /> Alle {active.length} anzeigen ({hidden} mehr)</>}
        </button>
      )}
      <ProjectAgentDisabledGroup projectId={projectId} agents={disabled} selectedAgentId={selectedAgentId} busy={busy}
        isAdmin={isAdmin} onSelect={onSelect} onEdit={onEdit} onDeleted={onDeleted} />
    </div>
  )
}
