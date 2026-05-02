import { Folder, GitBranch, Plus, Search, Tag, Users } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import type { Project } from "./types"

interface Props {
  projects: Project[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export function ProjectList({ projects, activeId, onSelect, onNew }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [search, setSearch] = useState("")

  const filtered = search.trim()
    ? projects.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.tags?.some(tag => tag.toLowerCase().includes(search.toLowerCase()))
      )
    : projects

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-white/[6%]">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("list_title")}</p>
        <div className="flex items-center gap-1">
          <HelpButton topic="projects" />
          <button
            onClick={onNew}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-zinc-300 hover:text-zinc-100 hover:bg-white/5 transition-colors"
          >
            <Plus size={13} /> {tCommon("actions.new")}
          </button>
        </div>
      </div>

      <div className="px-2 pt-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[3%] border border-white/[6%]">
          <Search size={11} className="text-zinc-500 flex-shrink-0" />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder={t("search_placeholder")}
            className="flex-1 bg-transparent text-xs text-zinc-300 placeholder-zinc-600 outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filtered.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-6">{t("no_projects")}</p>
        )}
        {filtered.map((p) => {
          const active = p.id === activeId
          const dim = p.status !== "active"
          return (
            <div
              key={p.id}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
                active
                  ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 border-l-2 border-violet-500"
                  : "hover:bg-white/[3%] border-l-2 border-transparent"
              } ${dim ? "opacity-50" : ""}`}
              onClick={() => onSelect(p.id)}
            >
              <Folder size={14} className={active ? "text-amber-300" : "text-zinc-500"} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${active ? "text-white" : "text-zinc-300"}`}>{p.name}</p>
                <div className="flex flex-wrap items-center gap-1 mt-0.5">
                  <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-violet-500/[8%] border border-violet-500/20 text-[10px] text-violet-300">
                    <Users size={9} /> {p.members.length}
                  </span>
                  {p.git_initialized && (
                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-emerald-500/[8%] border border-emerald-500/20 text-[10px] text-emerald-300">
                      <GitBranch size={9} /> git
                    </span>
                  )}
                  {p.status === "paused" && (
                    <span className="px-1.5 py-0.5 rounded-full bg-amber-500/[8%] border border-amber-500/20 text-[10px] text-amber-400">
                      paused
                    </span>
                  )}
                  {p.status === "archived" && (
                    <span className="px-1.5 py-0.5 rounded-full bg-zinc-500/[8%] border border-zinc-500/20 text-[10px] text-zinc-500">
                      archived
                    </span>
                  )}
                  {p.tags?.slice(0, 2).map(tag => (
                    <span key={tag} className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-sky-500/[8%] border border-sky-500/20 text-[10px] text-sky-300">
                      <Tag size={8} />{tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
