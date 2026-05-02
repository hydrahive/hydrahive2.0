import { useEffect, useState } from "react"
import { Folder, Loader2, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { OverviewTab } from "./_OverviewTab"
import { SessionsTab } from "./_SessionsTab"
import { GitTab } from "./_GitTab"
import { ServersTab } from "./_ServersTab"
import { StatsTab } from "./_StatsTab"
import { SettingsTab } from "./_SettingsTab"
import { NotesTab } from "./_NotesTab"
import type { Project } from "./types"

interface Props {
  project: Project
  onSaved: (p: Project) => void
  onDeleted: () => void
}

type Tab = "overview" | "notes" | "sessions" | "git" | "servers" | "stats" | "settings"

export function ProjectForm({ project, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(project)
  const [agentName, setAgentName] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("overview")

  useEffect(() => {
    setDraft(project)
    setTab("overview")
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

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: t("tabs.overview") },
    { id: "notes", label: t("tabs.notes") },
    { id: "sessions", label: t("tabs.sessions") },
    { id: "git", label: t("tabs.git") },
    { id: "servers", label: t("tabs.servers") },
    { id: "stats", label: t("tabs.stats") },
    { id: "settings", label: t("tabs.settings") },
  ]

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

      <div className="flex gap-1 px-6 pt-3 pb-0 border-b border-white/[6%]">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-2 text-xs font-medium rounded-t-md transition-colors border-b-2 -mb-px ${
              tab === t.id
                ? "text-violet-300 border-violet-500"
                : "text-zinc-500 border-transparent hover:text-zinc-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {error && (
          <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-sm text-rose-300">{error}</div>
        )}
        {tab === "overview" && <OverviewTab project={project} draft={draft} agentName={agentName} onChange={onSaved} onDraftChange={setDraft} />}
        {tab === "notes" && <NotesTab project={project} onSaved={onSaved} />}
        {tab === "sessions" && <SessionsTab projectId={project.id} />}
        {tab === "git" && <GitTab projectId={project.id} onChanged={() => projectsApi.get(project.id).then(onSaved)} />}
        {tab === "servers" && <ServersTab projectId={project.id} />}
        {tab === "stats" && <StatsTab projectId={project.id} />}
        {tab === "settings" && <SettingsTab project={project} draft={draft} onDraftChange={setDraft} onDeleted={onDeleted} />}
      </div>
    </div>
  )
}
