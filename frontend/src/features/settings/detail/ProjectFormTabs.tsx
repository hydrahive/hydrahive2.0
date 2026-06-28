import { useEffect, useState, type ComponentType } from "react"
import {
  Folder, Loader2, Save, LayoutGrid, StickyNote, GitBranch, Server,
  SlidersHorizontal, Users, FolderInput,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import { OverviewTab } from "@/features/projects/_OverviewTab"
import { GitTab } from "@/features/projects/_GitTab"
import { ServersTab } from "@/features/projects/_ServersTab"
import { MountsTab } from "@/features/projects/_MountsTab"
import { SettingsTab } from "@/features/projects/_SettingsTab"
import { SpecialistsTab } from "@/features/projects/_SpecialistsTab"
import { NotesTab } from "@/features/projects/_NotesTab"
import type { Project } from "@/features/projects/types"

interface Props {
  project: Project
  onSaved: (p: Project) => void
  onDeleted: () => void
}

/**
 * Projekt-EINSTELLUNGEN als Karteikarten-Reiter (Tills Schema). NUR Settings —
 * die Auswertungs-Tabs der alten ProjectForm (Statistiken, Sessions, Audit,
 * Dateien) bleiben bewusst draußen (Trennung Auswertung/Einstellung). Save/Draft-
 * Logik 1:1 wie ProjectForm.
 */
export function ProjectFormTabs({ project, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(project)
  const [agentName, setAgentName] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState("overview")

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

  const TABS: { id: string; icon: ComponentType<{ size?: number }>; label: string }[] = [
    { id: "overview", icon: LayoutGrid, label: t("tabs.overview") },
    { id: "settings", icon: SlidersHorizontal, label: t("tabs.settings") },
    { id: "specialists", icon: Users, label: t("tabs.specialists") },
    { id: "notes", icon: StickyNote, label: t("tabs.notes") },
    { id: "git", icon: GitBranch, label: t("tabs.git") },
    { id: "servers", icon: Server, label: t("tabs.servers") },
    { id: "mounts", icon: FolderInput, label: t("tabs.mounts") },
  ]

  return (
    <div className="flex h-full flex-col">
      {/* Header mit Name + Save */}
      <div className="flex items-center gap-4 border-b border-white/[6%] px-6 py-4">
        <Folder size={18} className="shrink-0 text-violet-300" />
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          className="min-w-0 flex-1 bg-transparent text-lg font-bold text-white focus:outline-none"
        />
        {dirty && (
          <button onClick={save} disabled={saving}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-violet-900/20 transition-all hover:from-indigo-500 hover:to-violet-500 disabled:opacity-30">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {tCommon("actions.save")}
          </button>
        )}
      </div>

      {/* Karteikarten-Reiter */}
      <div className="flex flex-wrap items-center gap-1 border-b border-white/8 px-4 pt-2">
        {TABS.map(({ id, icon: Icon, label }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm transition-colors ${
              tab === id ? "bg-[#104E8B]/20 text-sky-200 border-b-2 border-sky-400"
                         : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[4%]"
            }`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Reiter-Inhalt */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {error && (
          <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-sm text-rose-300">{error}</div>
        )}
        <div className="max-w-3xl">
          {tab === "overview" && <OverviewTab project={project} draft={draft} agentName={agentName} onChange={onSaved} onDraftChange={setDraft} />}
          {tab === "settings" && <SettingsTab project={project} draft={draft} onDraftChange={setDraft} onDeleted={onDeleted} />}
          {tab === "specialists" && <SpecialistsTab project={project} onSaved={onSaved} />}
          {tab === "notes" && <NotesTab project={project} onSaved={onSaved} />}
          {tab === "git" && <GitTab projectId={project.id} onChanged={() => projectsApi.get(project.id).then(onSaved)} />}
          {tab === "servers" && <ServersTab projectId={project.id} />}
          {tab === "mounts" && <MountsTab projectId={project.id} />}
        </div>
      </div>
    </div>
  )
}
