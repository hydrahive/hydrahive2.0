import { useId } from "react"
import type { Project } from "@/features/projects/types"

interface Props {
  projects: Project[]
  activeProjectId: string | null
  loading?: boolean
  onPick: (projectId: string | null) => void
}

export function ProjectSelector({ projects, activeProjectId, loading, onPick }: Props) {
  const selectId = useId()
  return (
    <div>
      {/* Kein zweites sichtbares „Projekt“-Etikett: der Kasten heißt schon so (Plan projekt-cockpit-kompakt). */}
      <label htmlFor={selectId} className="sr-only">Projekt wählen</label>
      <select
        id={selectId}
        value={activeProjectId ?? ""}
        disabled={loading || projects.length === 0}
        onChange={(e) => onPick(e.target.value || null)}
        title="Die Auswahl wird für dein Konto gespeichert."
        className="w-full rounded-[4px] border border-s-rand bg-s-tief px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none transition-colors hover:border-s-rand-hover disabled:opacity-50"
      >
        {projects.length === 0 ? (
          <option value="">Keine Projekte</option>
        ) : (
          projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)
        )}
      </select>
    </div>
  )
}
