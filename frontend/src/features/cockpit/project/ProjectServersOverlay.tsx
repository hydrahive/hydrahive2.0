import { ServersTab } from "@/features/projects/_ServersTab"
import type { Project } from "@/features/projects/types"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

export function ProjectServersOverlay({ project, onClose }: { project: Project; onClose: () => void }) {
  return <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="project-servers-title"><section className="flex h-[min(760px,94dvh)] w-full max-w-4xl flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#151c2b] shadow-2xl"><header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Infrastruktur</CockpitSectionLabel><h2 id="project-servers-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Server, VMs und Container</h2><p className="mt-1 text-xs text-[#8d9ab0]">{project.name}</p></div><CockpitButton onClick={onClose}>Schließen</CockpitButton></header><main className="min-h-0 flex-1 overflow-y-auto p-4"><div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-4"><ServersTab projectId={project.id} /></div></main><footer className="border-t border-[#2a364b] p-3 text-xs text-[#8d9ab0]">Zuweisen verändert nur die Projektbindung. Entfernen verlangt eine ausdrückliche Bestätigung.</footer></section></div>
}
