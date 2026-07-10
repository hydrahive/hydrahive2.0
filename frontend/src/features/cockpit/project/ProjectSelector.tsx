import type { Project } from "@/features/projects/types"

interface Props {
  projects: Project[]
  activeProjectId: string | null
  loading?: boolean
  onPick: (projectId: string | null) => void
}

export function ProjectSelector({ projects, activeProjectId, loading, onPick }: Props) {
  return (
    <div>
      <label className="mb-1 inline-flex rounded-[4px] border border-[#69d7ff]/35 bg-[#1c2940] px-2 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#69d7ff]">
        Projekt
      </label>
      <select
        value={activeProjectId ?? ""}
        disabled={loading || projects.length === 0}
        onChange={(e) => onPick(e.target.value || null)}
        className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none transition-colors hover:border-[#46617f] disabled:opacity-50"
      >
        {projects.length === 0 ? (
          <option value="">Keine Projekte</option>
        ) : (
          projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)
        )}
      </select>
      <p className="mt-1 text-[11px] text-[#8d9ab0]">Auswahl wird serverseitig pro User gespeichert.</p>
    </div>
  )
}
