import { MountsTab } from "@/features/projects/_MountsTab"
import type { Project } from "@/features/projects/types"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"
import { useDialogFokus } from "@/shared/dialog/useDialogFokus"

export function ProjectMountsOverlay({ project, onClose }: { project: Project; onClose: () => void }) {
  const dialogRef = useDialogFokus<HTMLDivElement>()
  return <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="project-mounts-title"><section className="flex h-[min(780px,94dvh)] w-full max-w-4xl flex-col overflow-hidden rounded-[6px] border border-s-rand-hover bg-s-box shadow-2xl"><header className="flex items-center justify-between border-b border-s-rand p-4"><div><CockpitSectionLabel>Dateien & Netzwerk</CockpitSectionLabel><h2 id="project-mounts-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Mounts und SMB-Freigaben</h2><p className="mt-1 text-xs text-[#9aa7bc]">{project.name}</p></div><CockpitButton onClick={onClose}>Schließen</CockpitButton></header><main className="min-h-0 flex-1 overflow-y-auto p-4"><div className="rounded-[4px] border border-s-rand bg-s-innen p-4"><MountsTab projectId={project.id} /></div></main><footer className="border-t border-s-rand p-3 text-xs text-[#9aa7bc]">Credentials werden nur über ihren gespeicherten Namen referenziert und niemals im Cockpit offengelegt.</footer></section></div>
}
