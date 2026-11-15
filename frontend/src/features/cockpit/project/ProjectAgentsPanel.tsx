import { useState } from "react"
import { ChevronDown, ChevronUp, Loader2, Pencil, Search, SquarePen } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { AgentBrief } from "@/features/chat/types"
import { teamList, visibleTeam } from "./agentTeam"
import { ProjectAgentTrashButton } from "./ProjectAgentTrashButton"

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
  /** Spezialist wurde über das Papierkorb-Symbol gelöscht/archiviert. */
  onDeleted?: (agentId: string) => void
}

/** So viele Agenten zeigt die Liste eingeklappt (Plan projekt-cockpit-kompakt). */
const LIMIT = 4
/** Ab so vielen Agenten erscheint die Suche. */
const SUCHE_AB = 8

/**
 * Projekt-Team, eine Zeile je Agent. Modell als Tooltip; Lead und gewählter Agent zeigen es
 * auch sichtbar. Deaktivierte Spezialisten stehen (ausgegraut, nicht auswählbar, ohne „Neue
 * Sitzung") am Ende der Liste — sichtbar bleiben sie bewusst, denn genau die will man oft
 * wegräumen (Till 15.11.: 1–2 Klicks über das Papierkorb-Symbol statt Umweg über Einstellungen).
 */
export function ProjectAgentsPanel({ agents, projectAgentId, specialistAgentIds = [], selectedAgentId, onSelect, onEdit, onNewSession, newSessionAgentId = null, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [expanded, setExpanded] = useState(false)
  const [query, setQuery] = useState("")
  const team = teamList(agents, projectAgentId, specialistAgentIds)
  const { shown, hidden } = visibleTeam(team, { selectedId: selectedAgentId, expanded, query, limit: LIMIT })
  // Während einer laufenden Übergabe alle Aktionen sperren — sonst entstehen bei Doppelklick zwei Sessions.
  const busy = newSessionAgentId !== null

  if (team.length === 0) return <p className="text-sm text-[#9aa7bc]">Keine Agenten oder Spezialisten gefunden.</p>

  return (
    <div className="space-y-1">
      {team.length >= SUCHE_AB && (
        <label className="mb-1.5 flex items-center gap-2 rounded-[4px] border border-s-rand bg-s-tief px-2 py-1 text-xs text-[#9aa7bc]">
          <Search size={12} aria-hidden="true" />
          <span className="sr-only">Team durchsuchen</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`${team.length} Agenten durchsuchen …`}
            className="min-w-0 flex-1 bg-transparent text-[#e8eef8] outline-none placeholder:text-[#9aa7bc]" />
        </label>
      )}
      {shown.map((agent) => {
        const isLead = agent.id === projectAgentId
        const isDisabled = !isLead && agent.status === "disabled"
        const selected = agent.id === selectedAgentId && !isDisabled
        const model = agent.llm_model || "Kein Modell zugewiesen"
        return (
          <div key={agent.id} data-team-agent={agent.id} data-team-agent-disabled={isDisabled || undefined}
            className={["flex items-center gap-1 rounded-[4px] border bg-s-innen transition-colors",
              isDisabled ? "border-s-rand opacity-55" : selected ? "border-[#69d7ff]/50 bg-[#1c2940]" : "border-s-rand hover:border-s-rand-hover"].join(" ")}>
            <button onClick={() => onSelect(agent.id)} disabled={busy || isDisabled} title={model}
              className={["min-w-0 flex-1 px-2 py-1.5 text-left text-sm font-semibold leading-tight disabled:cursor-not-allowed",
                selected ? "text-[#69d7ff]" : isDisabled ? "text-[#9aa7bc]" : "text-[#e8eef8]"].join(" ")}>
              <span className="flex items-center gap-1.5">
                <span className="truncate">{agent.name}</span>
                <span className="shrink-0 rounded-[3px] border border-s-rand px-1 py-px text-[8px] font-bold uppercase tracking-wide text-[#9aa7bc]">
                  {isLead ? "Lead" : "Spez."}
                </span>
                {isDisabled && (
                  <span className="shrink-0 rounded-[3px] border border-amber-500/30 bg-amber-500/10 px-1 py-px text-[8px] font-bold uppercase tracking-wide text-amber-300">
                    {t("team.disabled_badge")}
                  </span>
                )}
              </span>
              {(selected || isLead) && <span className="mt-0.5 block truncate font-mono text-[10px] font-normal text-[#9aa7bc]">{model}</span>}
            </button>
            {onNewSession && !isDisabled && (
              <button onClick={() => onNewSession(agent.id)} disabled={busy}
                className="rounded-[4px] p-1.5 text-[#9aa7bc] transition-colors hover:bg-white/[8%] hover:text-[#69d7ff] disabled:cursor-not-allowed disabled:opacity-40"
                title={`Neue Session mit ${agent.name} starten (bisherige Session wird übergeben)`}>
                {newSessionAgentId === agent.id ? <Loader2 size={13} className="animate-spin" /> : <SquarePen size={13} />}
              </button>
            )}
            {onEdit && (
              <button onClick={() => onEdit(agent.id)} disabled={busy}
                className="rounded-[4px] p-1.5 text-[#9aa7bc] hover:bg-white/[8%] hover:text-[#e8eef8] disabled:cursor-not-allowed disabled:opacity-40"
                title={`${isLead ? "Projekt-Agent" : "Spezialist"} bearbeiten`}>
                <Pencil size={13} />
              </button>
            )}
            {onDeleted && !isLead && isAdmin && (
              <ProjectAgentTrashButton agentId={agent.id} agentName={agent.name} disabled={busy} onDeleted={onDeleted} />
            )}
          </div>
        )
      })}
      {query.trim() && shown.length === 0 && <p className="px-1 text-xs text-[#9aa7bc]">Kein Agent passt zur Suche.</p>}
      {!query.trim() && team.length > LIMIT && (
        <button type="button" onClick={() => setExpanded((e) => !e)}
          className="flex w-full items-center justify-center gap-1 rounded-[4px] px-2 py-1 text-xs font-bold text-[#69d7ff] hover:bg-s-hebung">
          {expanded ? <><ChevronUp size={12} /> Weniger anzeigen</> : <><ChevronDown size={12} /> Alle {team.length} anzeigen ({hidden} mehr)</>}
        </button>
      )}
    </div>
  )
}
