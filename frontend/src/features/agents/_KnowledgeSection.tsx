import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ShieldAlert } from "lucide-react"
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { accessApi } from "@/features/access/api"
import type { AccessGroup } from "@/features/access/types"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import type { Agent } from "./types"
import { LEVELS, buildAccess, defaultsFor, levelOf, type KnowledgeInfo, type KnowledgeLevel } from "./knowledgeAccess"

/**
 * Bereich „Wissen“ im Agent-Editor (docs/specs/knowledge-spaces.md §2.4). Nur für Admins – der Server
 * lässt knowledge_access ohnehin nur über die Admin-Route ändern. Zeigt die wirksame Sicht und zählt,
 * wie viele Datamining-Einträge der Agent finden kann (gespeicherter Stand).
 */
export function KnowledgeSection({ draft, onChange }: { draft: Agent; onChange: (p: Partial<Agent>) => void }) {
  const { t } = useTranslation("agents")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const [projects, setProjects] = useState<Project[]>([])
  const [groups, setGroups] = useState<AccessGroup[]>([])
  const [info, setInfo] = useState<KnowledgeInfo | null>(null)

  useEffect(() => {
    if (!isAdmin) return
    projectsApi.list().then(setProjects).catch(() => setProjects([]))
    accessApi.groups().then(setGroups).catch(() => setGroups([]))
  }, [isAdmin])
  useEffect(() => {
    if (!isAdmin || !draft.id) return
    api.get<KnowledgeInfo>(`/agents/${draft.id}/knowledge`).then(setInfo).catch(() => setInfo(null))
  }, [isAdmin, draft.id, draft.updated_at])

  if (!isAdmin) return null
  const ka = draft.knowledge_access ?? {}
  const d = defaultsFor(draft.type)
  const cur = { scope: ka.scope ?? d.scope, projects: ka.projects ?? [], groups: ka.groups ?? [],
                max_level: levelOf(ka, draft.type) }
  const set = (p: Partial<typeof cur>) => onChange({ knowledge_access: buildAccess(draft.type, { ...cur, ...p }) })
  const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id])

  return (
    <div className="space-y-2 rounded-lg border border-white/[8%] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-zinc-200">{t("knowledge.title")}</p>
        {info && (
          <span className="text-[10px] text-zinc-500">
            {info.visible_events == null ? t("knowledge.count_unknown")
              : t("knowledge.count", { n: info.visible_events.toLocaleString(), user: info.counted_for })}
          </span>
        )}
      </div>
      <p className="text-[10px] text-zinc-500">{t("knowledge.hint")}</p>

      <label className="flex items-center gap-2 text-xs text-zinc-300">
        <span className="w-28 shrink-0 text-zinc-500">{t("knowledge.scope")}</span>
        <select value={cur.scope} onChange={(e) => set({ scope: e.target.value as "project" | "user" })}
          className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs">
          <option value="project">{t("knowledge.scope_project")}</option>
          <option value="user">{t("knowledge.scope_user")}</option>
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs text-zinc-300">
        <span className="w-28 shrink-0 text-zinc-500">{t("knowledge.level")}</span>
        <select value={cur.max_level} onChange={(e) => set({ max_level: e.target.value as KnowledgeLevel })}
          className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs">
          {LEVELS.map((l) => <option key={l} value={l}>{t(`knowledge.level_${l}`)}</option>)}
        </select>
      </label>
      {info?.limited_by_outward_tools && cur.max_level !== "normal" && (
        <p className="flex items-start gap-1.5 text-[10px] text-amber-300">
          <ShieldAlert size={12} className="mt-px shrink-0" />
          {t("knowledge.outward", { tools: info.outward_tools.join(", ") })}
        </p>
      )}

      {cur.scope === "project" && (
        <ChipList label={t("knowledge.projects")} empty={t("knowledge.none")}
          items={projects.filter((p) => p.id !== draft.project_id).map((p) => ({ id: p.id, name: p.name }))}
          selected={cur.projects} onToggle={(id) => set({ projects: toggle(cur.projects, id) })} />
      )}
      <ChipList label={t("knowledge.groups")} empty={t("knowledge.no_groups")}
        items={groups.map((g) => ({ id: g.id, name: g.name }))}
        selected={cur.groups} onToggle={(id) => set({ groups: toggle(cur.groups, id) })} />
      {cur.groups.length > 0 && <p className="text-[10px] text-zinc-500">{t("knowledge.groups_hint")}</p>}
    </div>
  )
}

function ChipList({ label, empty, items, selected, onToggle }: {
  label: string; empty: string; items: { id: string; name: string }[]; selected: string[]; onToggle: (id: string) => void
}) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-medium text-zinc-500">{label}</p>
      {items.length === 0 ? <p className="text-[10px] text-zinc-600">{empty}</p> : (
        <div className="flex flex-wrap gap-1.5">
          {items.map((it) => (
            <button key={it.id} type="button" onClick={() => onToggle(it.id)}
              className={`px-2 py-0.5 rounded-md border text-[11px] ${selected.includes(it.id)
                ? "bg-violet-500/15 border-violet-500/40 text-violet-200"
                : "border-white/[8%] text-zinc-400 hover:text-zinc-200"}`}>
              {it.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
