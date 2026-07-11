import { GitTab } from "@/features/projects/_GitTab"
import type { Project } from "@/features/projects/types"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

export function ProjectGitOverlay({ project, onClose, onChanged }: {
  project: Project
  onClose: () => void
  onChanged: () => void
}) {
  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="project-git-title">
      <section className="flex h-[min(820px,94dvh)] w-full max-w-5xl flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
        <header className="flex items-center justify-between border-b border-[#2a364b] p-4">
          <div>
            <CockpitSectionLabel>Versionsverwaltung</CockpitSectionLabel>
            <h2 id="project-git-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Git und Gitea verwalten</h2>
            <p className="mt-1 text-xs text-[#8d9ab0]">{project.name}</p>
          </div>
          <CockpitButton onClick={onClose}>Schließen</CockpitButton>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-4">
          <div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-4">
            <GitTab projectId={project.id} onChanged={onChanged} />
          </div>
        </main>
        <footer className="border-t border-[#2a364b] p-3 text-xs text-[#8d9ab0]">
          Git-Aktionen werden nur bewusst ausgelöst. Tokens werden nicht aus gespeicherten Daten geladen oder angezeigt.
        </footer>
      </section>
    </div>
  )
}
