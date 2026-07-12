import { useState, type ButtonHTMLAttributes, type ReactNode } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { CockpitButton } from "../CockpitButton"
import type { ProjectInsightView } from "./ProjectInsightsOverlay"

interface Props {
  disabled: boolean
  onCreate: () => void
  onEdit: () => void
  onAccess: () => void
  onServers: () => void
  onMounts: () => void
  onGit: () => void
  onIntegrations: () => void
  onInsight: (view: ProjectInsightView) => void
  onGraph: () => void
}

export function ProjectActionGroups({ disabled, onCreate, onEdit, onAccess, onServers, onMounts, onGit, onIntegrations, onInsight, onGraph }: Props) {
  return <div className="mt-3 space-y-2 border-t border-[#2a364b] pt-3">
    <div className="grid grid-cols-2 gap-2">
      <CockpitButton tone="primary" onClick={onCreate}>+ Neues Projekt</CockpitButton>
      <CockpitButton onClick={onEdit} disabled={disabled}>Bearbeiten</CockpitButton>
    </div>
    <ActionGroup title="Verwalten">
      <ActionButton onClick={onAccess} disabled={disabled}>Zugriff</ActionButton>
      <ActionButton onClick={onServers} disabled={disabled}>Server</ActionButton>
      <ActionButton onClick={onMounts} disabled={disabled}>Mounts</ActionButton>
      <ActionButton onClick={onGit} disabled={disabled}>Git</ActionButton>
      <ActionButton onClick={onIntegrations} disabled={disabled}>Integrationen</ActionButton>
    </ActionGroup>
    <ActionGroup title="Auswerten">
      <ActionButton onClick={() => onInsight("stats")} disabled={disabled}>Statistiken</ActionButton>
      <ActionButton onClick={() => onInsight("sessions")} disabled={disabled}>Sessions</ActionButton>
      <ActionButton onClick={() => onInsight("audit")} disabled={disabled}>Audit</ActionButton>
      <ActionButton onClick={onGraph} disabled={disabled}>Code-Graph</ActionButton>
    </ActionGroup>
  </div>
}

function ActionGroup({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return <div className="rounded-[4px] border border-[#2a364b] bg-[#101724]">
    <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open} className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-semibold text-[#b8c4d8] hover:bg-white/[3%]"><span>{title}</span>{open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}</button>
    {open && <div className="grid grid-cols-2 gap-1 border-t border-[#2a364b] p-2">{children}</div>}
  </div>
}

function ActionButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className="rounded-[4px] border border-transparent px-2 py-1.5 text-left text-xs text-[#8d9ab0] hover:border-[#2a364b] hover:bg-[#172133] hover:text-[#e8eef8] disabled:cursor-not-allowed disabled:opacity-40" />
}
