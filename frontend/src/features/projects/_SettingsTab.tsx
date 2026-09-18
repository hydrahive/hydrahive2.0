import { useEffect, useState } from "react"
import { Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { OverridesSection } from "./_SettingsOverrides"
import { SambaSection } from "./_SettingsSamba"
import type { Project } from "./types"

interface Props {
  project: Project
  draft: Project
  onDraftChange: (p: Project) => void
  onDeleted: () => void
}

export function SettingsTab({ project, draft, onDraftChange, onDeleted }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [samba, setSamba] = useState<{ enabled: boolean; share_name: string; user: string; password: string } | null>(null)
  const [sambaBusy, setSambaBusy] = useState(false)
  const [sambaError, setSambaError] = useState<string | null>(null)

  useEffect(() => {
    projectsApi.getSamba(project.id).then(setSamba).catch(() => setSamba(null))
  }, [project.id])

  async function toggleSamba() {
    if (!samba) return
    setSambaBusy(true); setSambaError(null)
    try {
      await projectsApi.putSamba(project.id, !samba.enabled)
      const fresh = await projectsApi.getSamba(project.id)
      setSamba(fresh)
    } catch (e) {
      setSambaError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setSambaBusy(false) }
  }

  async function remove() {
    if (!confirm(t("delete_confirm", { name: project.name }))) return
    await projectsApi.delete(project.id)
    onDeleted()
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <label className="block text-[10px] font-black uppercase tracking-[0.14em] text-[#8d9ab0]">
          {tCommon("labels.status")}
        </label>
        <select
          value={draft.status}
          onChange={(e) => onDraftChange({ ...draft, status: e.target.value as Project["status"] })}
          className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"
        >
          <option value="active">{tCommon("status.active")}</option>
          <option value="paused">{tCommon("status.paused")}</option>
          <option value="archived">{tCommon("status.archived")}</option>
        </select>
      </div>

      {samba && (
        <SambaSection samba={samba} busy={sambaBusy} error={sambaError} onToggle={toggleSamba} />
      )}

      <OverridesSection project={project} onSaved={onDraftChange} />

      <div className="border-t border-[#2a364b] pt-4">
        <p className="mb-3 text-[10px] font-black uppercase tracking-[0.14em] text-[#718097]">{t("settings.danger_zone")}</p>
        <button onClick={remove}
          className="flex items-center gap-2 rounded-[4px] border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs font-bold text-rose-200 transition-colors hover:bg-rose-500/15">
          <Trash2 size={14} />
          {t("settings.delete_project")}
        </button>
      </div>
    </div>
  )
}
