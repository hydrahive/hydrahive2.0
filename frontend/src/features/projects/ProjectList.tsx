import { Folder, Plus } from "lucide-react"
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

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {projects.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-6">{t("no_projects")}</p>
        )}
        {projects.map((p) => {
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
              <Folder size={14} className={active ? "text-violet-300" : "text-zinc-500"} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${active ? "text-white" : "text-zinc-300"}`}>{p.name}</p>
                <p className="text-xs text-zinc-600 mt-0.5 truncate">
                  {t("fields.members_count", { count: p.members.length })} · {p.git_initialized ? t("fields.git_init") : t("fields.git_init_no")}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
