import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { AgentBrief } from "@/features/chat/types"
import { ProjectAgentRow } from "./ProjectAgentRow"

const lsKey = (projectId: string | null | undefined) => `hh2.cockpit.disabled_team_open.${projectId ?? "_"}`

function readOpen(projectId: string | null | undefined): boolean {
  try {
    return localStorage.getItem(lsKey(projectId)) === "1"
  } catch {
    return false
  }
}

interface Props {
  projectId?: string | null
  agents: AgentBrief[]
  selectedAgentId?: string | null
  busy: boolean
  isAdmin: boolean
  onSelect: (agentId: string) => void
  onEdit?: (agentId: string) => void
  onDeleted?: (agentId: string) => void
}

/**
 * Eigene, einklappbare Gruppe für deaktivierte Spezialisten — unterliegt NICHT dem LIMIT/der
 * Suche der normalen Team-Liste (siehe agentTeam.splitTeam). Einmal pro Projekt aufgeklappt
 * (Zustand in localStorage, bleibt über Sessions erhalten, wie CollapsibleBox), ist danach
 * jeder deaktivierte Spezialist mit genau 2 Klicks erreichbar: Papierkorb → „Ins Archiv
 * starten". Till 15.11.: genau die alten/deaktivierten Spezialisten sollten so wegräumbar sein.
 */
export function ProjectAgentDisabledGroup({ projectId, agents, selectedAgentId, busy, isAdmin, onSelect, onEdit, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const [open, setOpen] = useState(() => readOpen(projectId))

  if (agents.length === 0) return null

  function toggle() {
    setOpen((current) => {
      const next = !current
      try { localStorage.setItem(lsKey(projectId), next ? "1" : "0") } catch { /* ignore */ }
      return next
    })
  }

  return (
    <div className="mt-1 space-y-1" data-team-disabled-group>
      <button type="button" onClick={toggle} aria-expanded={open}
        className="flex w-full items-center gap-1.5 rounded-[4px] px-2 py-1 text-xs font-bold text-amber-300/80 hover:bg-s-hebung">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {t("team.disabled_group", { count: agents.length })}
      </button>
      {open && agents.map((agent) => (
        <ProjectAgentRow key={agent.id} agent={agent} isLead={false} isDisabled selected={agent.id === selectedAgentId}
          busy={busy} isAdmin={isAdmin} onSelect={onSelect} onEdit={onEdit} onDeleted={onDeleted} />
      ))}
    </div>
  )
}
