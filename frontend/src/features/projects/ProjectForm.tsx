import { useEffect, useState } from "react"
import {
  Folder, Loader2, Save, LayoutGrid, BarChart3, StickyNote, FolderOpen,
  MessageSquare, GitBranch, Server, SlidersHorizontal, Users, ScrollText,
  FolderInput,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { projectsApi } from "./api"
import { OverviewTab } from "./_OverviewTab"
import { SessionsTab } from "./_SessionsTab"
import { GitTab } from "./_GitTab"
import { ServersTab } from "./_ServersTab"
import { MountsTab } from "./_MountsTab"
import { StatsTab } from "./_StatsTab"
import { SettingsTab } from "./_SettingsTab"
import { SpecialistsTab } from "./_SpecialistsTab"
import { NotesTab } from "./_NotesTab"
import { FilesTab } from "./_FilesTab"
import { AuditTab } from "./_AuditTab"
import type { Project } from "./types"

interface Props {
  project: Project
  onSaved: (p: Project) => void
  onDeleted: () => void
}

const C = rgbFor("/projects")
const BOX = "box-static mb-3 break-inside-avoid"
// Lange Listen: höhengedeckelt → intern scrollen statt sprawl.
const SCROLL = "max-h-[28rem] overflow-y-auto"

export function ProjectForm({ project, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(project)
  const [agentName, setAgentName] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(project)
    projectsApi.getAgent(project.id).then((a) => setAgentName(a.name)).catch(() => setAgentName(""))
  }, [project.id])

  const dirty = draft.name !== project.name || draft.description !== project.description || draft.status !== project.status

  async function save() {
    setSaving(true); setError(null)
    try {
      const updated = await projectsApi.update(project.id, {
        name: draft.name, description: draft.description, status: draft.status,
      })
      onSaved(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setSaving(false) }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[6%] flex items-center gap-4">
        <Folder size={18} className="text-violet-300 flex-shrink-0" />
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          className="flex-1 bg-transparent text-lg font-bold text-white focus:outline-none min-w-0"
        />
        {dirty && (
          <button
            onClick={save} disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 transition-all shadow-md shadow-violet-900/20"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {tCommon("actions.save")}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {error && (
          <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-sm text-rose-300">{error}</div>
        )}

        {/* Übersicht: volle Breite, ganz oben (außerhalb des Masonry-Grids). */}
        <CollapsibleBox boxId="project-overview" color={C} className="box-static mb-3" icon={<LayoutGrid size={14} />} title={t("tabs.overview")}>
          <div className="box-b"><OverviewTab project={project} draft={draft} agentName={agentName} onChange={onSaved} onDraftChange={setDraft} /></div>
        </CollapsibleBox>

        <div className="columns-1 xl:columns-2 2xl:columns-3 gap-3">
          <CollapsibleBox boxId="project-stats" color={C} className={BOX} icon={<BarChart3 size={14} />} title={t("tabs.stats")}>
            <div className="box-b"><StatsTab projectId={project.id} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-sessions" color={C} className={BOX} icon={<MessageSquare size={14} />} title={t("tabs.sessions")}>
            <div className={`box-b ${SCROLL}`}><SessionsTab projectId={project.id} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-notes" color={C} className={BOX} icon={<StickyNote size={14} />} title={t("tabs.notes")}>
            <div className="box-b"><NotesTab project={project} onSaved={onSaved} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-files" color={C} className={BOX} icon={<FolderOpen size={14} />} title={t("tabs.files")} defaultCollapsed>
            <div className={`box-b ${SCROLL}`}><FilesTab projectId={project.id} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-git" color={C} className={BOX} icon={<GitBranch size={14} />} title={t("tabs.git")} defaultCollapsed>
            <div className="box-b"><GitTab projectId={project.id} onChanged={() => projectsApi.get(project.id).then(onSaved)} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-servers" color={C} className={BOX} icon={<Server size={14} />} title={t("tabs.servers")} defaultCollapsed>
            <div className={`box-b ${SCROLL}`}><ServersTab projectId={project.id} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-mounts" color={C} className={BOX} icon={<FolderInput size={14} />} title={t("tabs.mounts")} defaultCollapsed>
            <div className={`box-b ${SCROLL}`}><MountsTab projectId={project.id} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-settings" color={C} className={BOX} icon={<SlidersHorizontal size={14} />} title={t("tabs.settings")} defaultCollapsed>
            <div className="box-b"><SettingsTab project={project} draft={draft} onDraftChange={setDraft} onDeleted={onDeleted} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-specialists" color={C} className={BOX} icon={<Users size={14} />} title={t("tabs.specialists")} defaultCollapsed>
            <div className="box-b"><SpecialistsTab project={project} onSaved={onSaved} /></div>
          </CollapsibleBox>

          <CollapsibleBox boxId="project-audit" color={C} className={BOX} icon={<ScrollText size={14} />} title={t("tabs.audit")} defaultCollapsed>
            <div className={`box-b ${SCROLL}`}><AuditTab projectId={project.id} /></div>
          </CollapsibleBox>
        </div>
      </div>
    </div>
  )
}
