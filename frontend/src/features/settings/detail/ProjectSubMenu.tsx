import { useCallback, useEffect, useState } from "react"
import { Folder, Users, GitBranch, Plus, Tag } from "lucide-react"
import { projectsApi } from "@/features/projects/api"
import { NewProjectDialog } from "@/features/projects/NewProjectDialog"
import type { Project } from "@/features/projects/types"

interface Props {
  activeItem: string | null
  onSelect: (id: string) => void
}

// Sortierung: aktive zuerst, dann pausiert, dann archiviert; je Name.
const STATUS_ORDER: Record<string, number> = { active: 0, paused: 1, archived: 2 }

/**
 * Submenü der Projekte-Gruppe: echte Projektliste mit Member-/Git-/Status-Pills,
 * sortiert, ohne Button davor (Tills Schema).
 */
export function ProjectSubMenu({ activeItem, onSelect }: Props) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    projectsApi.list()
      .then((list) => {
        const sorted = [...list].sort((a, b) => {
          const o = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9)
          return o !== 0 ? o : a.name.localeCompare(b.name)
        })
        setProjects(sorted)
      })
      .catch(() => setProjects([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-white/8 px-4 py-3">
        <h2 className="text-sm font-semibold text-zinc-200">Projekte</h2>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1 rounded-md border border-violet-500/30 bg-violet-500/10 px-2 py-1 text-xs text-violet-300 hover:bg-violet-500/20"
        >
          <Plus size={12} /> Neu
        </button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {loading ? (
          <div className="h-20 animate-pulse rounded-lg bg-zinc-900/50" />
        ) : projects.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-zinc-600">Keine Projekte.</p>
        ) : (
          projects.map((p) => {
            const active = p.id === activeItem
            const dim = p.status !== "active"
            return (
              <div
                key={p.id}
                onClick={() => onSelect(p.id)}
                className={`group flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 transition-all ${
                  active
                    ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 border-l-2 border-violet-500"
                    : "border-l-2 border-transparent hover:bg-white/[3%]"
                } ${dim ? "opacity-50" : ""}`}
              >
                <Folder size={14} className={active ? "text-amber-300" : "text-zinc-500"} />
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-sm ${active ? "text-white" : "text-zinc-300"}`}>{p.name}</p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1">
                    <span className="flex items-center gap-0.5 rounded-full border border-violet-500/20 bg-violet-500/[8%] px-1.5 py-0.5 text-[10px] text-violet-300">
                      <Users size={9} /> {p.members.length}
                    </span>
                    {p.git_initialized && (
                      <span className="flex items-center gap-0.5 rounded-full border border-emerald-500/20 bg-emerald-500/[8%] px-1.5 py-0.5 text-[10px] text-emerald-300">
                        <GitBranch size={9} /> git
                      </span>
                    )}
                    {p.status === "paused" && (
                      <span className="rounded-full border border-amber-500/20 bg-amber-500/[8%] px-1.5 py-0.5 text-[10px] text-amber-400">paused</span>
                    )}
                    {p.status === "archived" && (
                      <span className="rounded-full border border-zinc-500/20 bg-zinc-500/[8%] px-1.5 py-0.5 text-[10px] text-zinc-500">archived</span>
                    )}
                    {p.tags?.slice(0, 1).map((tag) => (
                      <span key={tag} className="flex items-center gap-0.5 rounded-full border border-sky-500/20 bg-sky-500/[8%] px-1.5 py-0.5 text-[10px] text-sky-300">
                        <Tag size={8} />{tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {creating && (
        <NewProjectDialog
          onClose={() => setCreating(false)}
          onCreated={(id) => {
            setCreating(false)
            load()
            onSelect(id)
          }}
        />
      )}
    </div>
  )
}
