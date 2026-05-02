import { useState } from "react"
import { Loader2, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { Project } from "./types"

interface Props {
  project: Project
  onSaved: (p: Project) => void
}

export function NotesTab({ project, onSaved }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [notes, setNotes] = useState(project.notes ?? "")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dirty = notes !== (project.notes ?? "")

  async function save() {
    setSaving(true); setError(null)
    try {
      const updated = await projectsApi.update(project.id, { notes })
      onSaved(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setSaving(false) }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">{t("notes.hint")}</p>
      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-sm text-rose-300">{error}</div>
      )}
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={20}
        placeholder={t("notes.placeholder")}
        className="w-full rounded-lg border border-white/[8%] bg-white/[3%] px-4 py-3 text-sm text-zinc-200 placeholder-zinc-600 font-mono resize-y focus:outline-none focus:border-violet-500/50"
      />
      {dirty && (
        <button
          onClick={save} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 transition-all"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {tCommon("actions.save")}
        </button>
      )}
    </div>
  )
}
