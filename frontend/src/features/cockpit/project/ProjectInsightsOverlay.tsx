import { AuditTab } from "@/features/projects/_AuditTab"
import { SessionsTab } from "@/features/projects/_SessionsTab"
import { StatsTab } from "@/features/projects/_StatsTab"
import type { Project } from "@/features/projects/types"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

export type ProjectInsightView = "stats" | "sessions" | "audit"

const VIEW_COPY: Record<ProjectInsightView, { eyebrow: string; title: string; footer: string }> = {
  stats: {
    eyebrow: "Projektübersicht",
    title: "Statistiken",
    footer: "Die Werte stammen aus der bestehenden Projektstatistik und lösen kein Datamining aus.",
  },
  sessions: {
    eyebrow: "Projektverlauf",
    title: "Sessions",
    footer: "Ein Klick auf eine Session öffnet sie direkt in der Werkstatt.",
  },
  audit: {
    eyebrow: "Nachvollziehbarkeit",
    title: "Audit",
    footer: "Projektaktivitäten lassen sich nach Aktion und Benutzer filtern.",
  },
}

export function ProjectInsightsOverlay({ project, view, onClose }: {
  project: Project
  view: ProjectInsightView
  onClose: () => void
}) {
  const copy = VIEW_COPY[view]
  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="project-insights-title">
      <section className="flex h-[min(760px,94dvh)] w-full max-w-4xl flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
        <header className="flex items-center justify-between border-b border-[#2a364b] p-4">
          <div>
            <CockpitSectionLabel>{copy.eyebrow}</CockpitSectionLabel>
            <h2 id="project-insights-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">{copy.title}</h2>
            <p className="mt-1 text-xs text-[#8d9ab0]">{project.name}</p>
          </div>
          <CockpitButton onClick={onClose}>Schließen</CockpitButton>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-4">
          <div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-4">
            {view === "stats" && <StatsTab projectId={project.id} />}
            {view === "sessions" && <SessionsTab projectId={project.id} />}
            {view === "audit" && <AuditTab projectId={project.id} />}
          </div>
        </main>
        <footer className="border-t border-[#2a364b] p-3 text-xs text-[#8d9ab0]">{copy.footer}</footer>
      </section>
    </div>
  )
}
