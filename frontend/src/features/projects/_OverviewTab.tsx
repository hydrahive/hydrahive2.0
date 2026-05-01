import { ExternalLink, GitBranch } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { MemberManager } from "./MemberManager"
import type { Project } from "./types"

interface Props {
  project: Project
  draft: Project
  agentName: string
  onChange: (p: Project) => void
  onDraftChange: (p: Project) => void
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</label>
      {children}
    </div>
  )
}

export function OverviewTab({ project, draft, agentName, onChange, onDraftChange }: Props) {
  const { t, i18n } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")

  return (
    <div className="space-y-6">
      <Field label={tCommon("labels.description")}>
        <textarea
          value={draft.description} rows={3}
          onChange={(e) => onDraftChange({ ...draft, description: e.target.value })}
          className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200 leading-relaxed resize-none"
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
        <MemberManager project={project} onChange={onChange} />
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
  )
}
