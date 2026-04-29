import { useEffect, useState } from "react"
import { Folder, Loader2, Save, Trash2, ExternalLink, GitBranch } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { MemberManager } from "./MemberManager"
import type { Project } from "./types"

interface Props {
  project: Project
  onSaved: (p: Project) => void
  onDeleted: () => void
}

export function ProjectForm({ project, onSaved, onDeleted }: Props) {
  const { t, i18n } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(project)
  const [agentName, setAgentName] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(project)
    projectsApi.getAgent(project.id).then((a) => setAgentName(a.name)).catch(() => setAgentName(""))
  }, [project.id])

  const dirty =
    draft.name !== project.name ||
    draft.description !== project.description ||
    draft.status !== project.status

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

  async function remove() {
    if (!confirm(t("delete_confirm", { name: project.name }))) return
    await projectsApi.delete(project.id)
    onDeleted()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[6%] flex items-center gap-4">
        <Folder size={18} className="text-violet-300 flex-shrink-0" />
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          className="flex-1 bg-transparent text-lg font-bold text-white focus:outline-none"
        />
        <select
          value={draft.status}
          onChange={(e) => setDraft({ ...draft, status: e.target.value as Project["status"] })}
          className="px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/[8%] text-xs text-zinc-300"
        >
          <option value="active">{tCommon("status.active")}</option>
          <option value="archived">{tCommon("status.archived")}</option>
        </select>
        <button
          onClick={save} disabled={!dirty || saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md shadow-violet-900/20"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {tCommon("actions.save")}
        </button>
        <button
          onClick={remove}
          className="p-2 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-sm text-rose-300">{error}</div>
        )}

        <Field label={tCommon("labels.description")}>
          <textarea
            value={draft.description} rows={3}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200 leading-relaxed"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label={t("fields.agent")}>
            <Link
              to="/agents"
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-violet-500/[6%] border border-violet-500/20 text-sm text-violet-200 hover:bg-violet-500/[10%] transition-colors"
            >
              <span className="flex-1 truncate">{agentName || t("fields.agent_loading")}</span>
              <ExternalLink size={12} />
            </Link>
          </Field>
          <Field label={t("fields.workspace")}>
            <p className="px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-xs text-zinc-400 font-mono flex items-center gap-2">
              {project.git_initialized && <GitBranch size={12} className="text-violet-400" />}
              data/workspaces/projects/{project.id.slice(0, 8)}…
            </p>
          </Field>
        </div>

        <Field label={t("fields.members_label", { count: project.members.length })}>
          <MemberManager project={project} onChange={onSaved} />
        </Field>

        <Field label={tCommon("labels.created_at")}>
          <p className="text-xs text-zinc-500">
            {t("fields.created_by", {
              date: new Date(project.created_at).toLocaleString(i18n.language),
              user: project.created_by,
            })}
          </p>
        </Field>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</label>
      {children}
    </div>
  )
}
