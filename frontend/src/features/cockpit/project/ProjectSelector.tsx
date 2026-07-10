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
      <label className="mb-1 block text-[10px] font-black uppercase tracking-[0.14em] text-cyan-300/80">
        Projekt
      </label>
      <select
        value={activeProjectId ?? ""}
        disabled={loading || projects.length === 0}
        onChange={(e) => onPick(e.target.value || null)}
        className="w-full rounded-[4px] border border-white/[10%] bg-zinc-950/70 px-3 py-2 text-sm font-semibold text-zinc-100 outline-none transition-colors hover:border-cyan-400/30 disabled:opacity-50"
      >
        {projects.length === 0 ? (
          <option value="">Keine Projekte</option>
        ) : (
          projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)
        )}
      </select>
      <p className="mt-1 text-[11px] text-zinc-600">Auswahl wird serverseitig pro User gespeichert.</p>
    </div>
  )
}
