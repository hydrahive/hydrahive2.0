import { Loader2, Pencil, SquarePen } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { AgentBrief } from "@/features/chat/types"
import { ProjectAgentTrashButton } from "./ProjectAgentTrashButton"

interface Props {
  agent: AgentBrief
  isLead: boolean
  isDisabled: boolean
  selected: boolean
  busy: boolean
  isAdmin: boolean
  onSelect: (agentId: string) => void
  onEdit?: (agentId: string) => void
  onNewSession?: (agentId: string) => void
  newSessionAgentId?: string | null
  onDeleted?: (agentId: string) => void
}

/**
 * Eine Zeile im Projekt-Team — ausgelagert aus ProjectAgentsPanel, damit sowohl die normale
 * Liste als auch die Gruppe „Deaktiviert" (ProjectAgentDisabledGroup) dieselbe Darstellung
 * nutzen. Deaktivierte Spezialisten: ausgegraut, nicht auswählbar, kein „Neue Sitzung"-Knopf
 * (ein deaktivierter Agent kann laut runner.py nicht laufen), aber MIT Stift und — für Admins —
 * mit direktem Papierkorb-Symbol (1–2-Klick-Löschweg, Till 15.11.).
 */
export function ProjectAgentRow({ agent, isLead, isDisabled, selected, busy, isAdmin, onSelect, onEdit, onNewSession, newSessionAgentId = null, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const model = agent.llm_model || "Kein Modell zugewiesen"

  return (
    <div data-team-agent={agent.id} data-team-agent-disabled={isDisabled || undefined}
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
}
