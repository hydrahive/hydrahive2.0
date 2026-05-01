import { AlertTriangle, Folder, MessageCircle, Plus, Trash2 } from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { ProjectBrief } from "./api"
import type { Session } from "./types"

type Tab = "direct" | "projects"

interface Props {
  sessions: Session[]
  activeId: string | null
  knownAgentIds: Set<string>
  projects: ProjectBrief[]
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNew: () => void
}

export function SessionList({ sessions, activeId, knownAgentIds, projects, onSelect, onDelete, onNew }: Props) {
  const { t } = useTranslation("chat")
  const { t: tCommon } = useTranslation("common")
  const [tab, setTab] = useState<Tab>("direct")
  const projectMap = useMemo(() => new Map(projects.map((p) => [p.id, p])), [projects])

  const direct = sessions.filter((s) => !s.project_id)
  const projectSessions = sessions.filter((s) => !!s.project_id)

  const grouped = useMemo(() => {
    const m = new Map<string, Session[]>()
    for (const s of projectSessions) {
      const key = s.project_id ?? ""
      const arr = m.get(key) ?? []
      arr.push(s)
      m.set(key, arr)
    }
    return m
  }, [projectSessions])

  const visible = tab === "direct" ? direct : projectSessions

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-white/[6%]">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("session.list_title")}</p>
        <button
          onClick={onNew}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-zinc-300 hover:text-zinc-100 hover:bg-white/5 transition-colors"
        >
          <Plus size={13} /> {tCommon("actions.new")}
        </button>
      </div>

      <div className="flex border-b border-white/[6%] text-xs">
        <TabButton active={tab === "direct"} onClick={() => setTab("direct")} icon={MessageCircle} label={t("tabs.direct")} count={direct.length} />
        <TabButton active={tab === "projects"} onClick={() => setTab("projects")} icon={Folder} label={t("tabs.projects")} count={projectSessions.length} />
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {visible.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-6">
            {tab === "direct" ? t("session.no_direct") : t("session.no_project")}
          </p>
        )}
        {tab === "direct" && direct.map((s) => (
          <SessionRow key={s.id} session={s} active={s.id === activeId}
            orphaned={!knownAgentIds.has(s.agent_id)}
            onSelect={onSelect} onDelete={onDelete} />
        ))}
        {tab === "projects" && Array.from(grouped.entries()).map(([pid, items]) => (
          <div key={pid} className="mb-3">
            <p className="text-[10.5px] font-semibold uppercase tracking-wider text-zinc-500 px-2 py-1 truncate">
              {projectMap.get(pid)?.name ?? t("session.unknown_project")}
            </p>
            {items.map((s) => (
              <SessionRow key={s.id} session={s} active={s.id === activeId}
                orphaned={!knownAgentIds.has(s.agent_id)}
                onSelect={onSelect} onDelete={onDelete} />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function TabButton({ active, onClick, icon: Icon, label, count }: {
  active: boolean; onClick: () => void; icon: typeof Folder; label: string; count: number
}) {
  return (
    <button onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 transition-all border-b-2 ${
        active ? "border-violet-500 text-zinc-200 bg-white/[3%]" : "border-transparent text-zinc-500 hover:text-zinc-300"
      }`}>
      <Icon size={12} /> {label} <span className="opacity-60">({count})</span>
    </button>
  )
}

function SessionRow({ session, active, orphaned, onSelect, onDelete }: {
  session: Session; active: boolean; orphaned: boolean
  onSelect: (id: string) => void; onDelete: (id: string) => void
}) {
  const { t, i18n } = useTranslation("chat")
  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
        active
          ? "bg-[var(--hh-accent-soft)] border-l-2 border-[var(--hh-accent)]"
          : "hover:bg-white/[3%] border-l-2 border-transparent"
      } ${orphaned ? "opacity-50" : ""}`}
      onClick={() => onSelect(session.id)}
    >
      <div className="flex-1 min-w-0">
        <p className={`text-sm truncate flex items-center gap-1.5 ${active ? "text-white" : "text-zinc-300"}`}>
          {orphaned && <AlertTriangle size={11} className="text-amber-400 flex-shrink-0" />}
          <span className="truncate">{session.title || t("session.without_title")}</span>
        </p>
        <p className="text-xs text-zinc-600 mt-0.5">
          {orphaned ? `${t("session.orphaned")} · ` : ""}
          {new Date(session.updated_at).toLocaleString(i18n.language, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
      <button onClick={(e) => { e.stopPropagation(); if (confirm(t("session.delete_confirm"))) onDelete(session.id) }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all">
        <Trash2 size={13} />
      </button>
    </div>
  )
}
