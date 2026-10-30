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
  onSkills: () => void
  onInsight: (view: ProjectInsightView) => void
  onGraph: () => void
}

export function ProjectActionGroups({ disabled, onCreate, onEdit, onAccess, onServers, onMounts, onGit, onIntegrations, onSkills, onInsight, onGraph }: Props) {
  const [open, setOpen] = useState<"verwalten" | "auswerten" | null>(null)
  const toggle = (g: "verwalten" | "auswerten") => setOpen((cur) => (cur === g ? null : g))
  // Zwei Gruppen nebeneinander, aufgeklappt über die volle Breite (Plan projekt-cockpit-kompakt).
  return <div className="mt-2 space-y-2 border-t border-s-rand pt-2">
    <div className="grid grid-cols-2 gap-2">
      <CockpitButton tone="primary" onClick={onCreate}>+ Neues Projekt</CockpitButton>
      <CockpitButton onClick={onEdit} disabled={disabled}>Bearbeiten</CockpitButton>
      <GroupToggle title="Verwalten" open={open === "verwalten"} onClick={() => toggle("verwalten")} />
      <GroupToggle title="Auswerten" open={open === "auswerten"} onClick={() => toggle("auswerten")} />
    </div>
    {open === "verwalten" && <ActionGroup>
      <ActionButton onClick={onAccess} disabled={disabled}>Zugriff</ActionButton>
      <ActionButton onClick={onServers} disabled={disabled}>Server</ActionButton>
      <ActionButton onClick={onMounts} disabled={disabled}>Externe Mounts</ActionButton>
      <ActionButton onClick={onGit} disabled={disabled}>Git</ActionButton>
      <ActionButton onClick={onIntegrations} disabled={disabled}>Samba &amp; Integrationen</ActionButton>
      <ActionButton onClick={onSkills} disabled={disabled}>Skills</ActionButton>
    </ActionGroup>}
    {open === "auswerten" && <ActionGroup>
      <ActionButton onClick={() => onInsight("stats")} disabled={disabled}>Statistiken</ActionButton>
      <ActionButton onClick={() => onInsight("sessions")} disabled={disabled}>Sessions</ActionButton>
      <ActionButton onClick={() => onInsight("audit")} disabled={disabled}>Audit</ActionButton>
      <ActionButton onClick={onGraph} disabled={disabled}>Code-Graph</ActionButton>
    </ActionGroup>}
  </div>
}

function GroupToggle({ title, open, onClick }: { title: string; open: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} aria-expanded={open}
    className={`flex items-center justify-between rounded-[4px] border px-2.5 py-1.5 text-left text-xs font-semibold hover:bg-s-hebung ${
      open ? "border-s-rand-hover bg-s-hebung text-[#e8eef8]" : "border-s-rand bg-s-innen text-[#b8c4d8]"}`}>
    <span>{title}</span>{open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
  </button>
}

function ActionGroup({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-1 rounded-[4px] border border-s-rand bg-s-innen p-2">{children}</div>
}

function ActionButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className="rounded-[4px] border border-transparent px-2 py-1.5 text-left text-xs text-[#9aa7bc] hover:border-s-rand-hover hover:bg-s-hebung hover:text-[#e8eef8] disabled:cursor-not-allowed disabled:opacity-40" />
}
