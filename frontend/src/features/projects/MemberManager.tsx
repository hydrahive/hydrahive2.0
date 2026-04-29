import { useEffect, useState } from "react"
import { Plus, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi, usersApi } from "./api"
import type { Project } from "./types"

interface Props {
  project: Project
  onChange: (p: Project) => void
}

export function MemberManager({ project, onChange }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [available, setAvailable] = useState<string[]>([])
  const [adding, setAdding] = useState("")

  useEffect(() => {
    usersApi.list().then((users) => setAvailable(users.map((u) => u.username))).catch(() => {})
  }, [])

  async function add() {
    if (!adding) return
    try {
      const updated = await projectsApi.addMember(project.id, adding)
      onChange(updated)
      setAdding("")
    } catch (e) {
      alert(e instanceof Error ? e.message : tCommon("status.error"))
    }
  }

  async function remove(username: string) {
    if (!confirm(t("members.remove_confirm", { username }))) return
    const updated = await projectsApi.removeMember(project.id, username)
    onChange(updated)
  }

  const candidates = available.filter((u) => !project.members.includes(u))

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {project.members.length === 0 && (
          <p className="text-xs text-zinc-600">{t("members.no_members")}</p>
        )}
        {project.members.map((m) => (
          <span
            key={m}
            className="inline-flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-md bg-violet-500/[8%] border border-violet-500/20 text-xs text-violet-200"
          >
            {m}
            <button
              onClick={() => remove(m)}
              className="p-0.5 rounded hover:bg-rose-500/20 hover:text-rose-300 transition-colors"
            >
              <X size={11} />
            </button>
          </span>
        ))}
      </div>
      {candidates.length > 0 && (
        <div className="flex gap-2">
          <select
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
            className="flex-1 px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200"
          >
            <option value="">{t("members.select_user")}</option>
            {candidates.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
          <button
            onClick={add}
            disabled={!adding}
            className="flex items-center gap-1 px-3 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm disabled:opacity-30"
          >
            <Plus size={13} /> {tCommon("actions.add")}
          </button>
        </div>
      )}
    </div>
  )
}
