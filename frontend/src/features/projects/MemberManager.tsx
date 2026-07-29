import { useEffect, useState } from "react"
import { Plus, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi, usersApi } from "./api"
import type { Project, ProjectRole } from "./types"

interface Props {
  project: Project
  onChange: (p: Project) => void
}

const ROLES: ProjectRole[] = ["read", "write", "admin"]

const ROLE_STYLE: Record<ProjectRole, string> = {
  read: "bg-sky-500/[8%] border-sky-500/20 text-sky-200",
  write: "bg-violet-500/[8%] border-violet-500/20 text-violet-200",
  admin: "bg-amber-500/[8%] border-amber-500/20 text-amber-200",
}

export function MemberManager({ project, onChange }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [available, setAvailable] = useState<string[]>([])
  const [adding, setAdding] = useState("")
  const [addRole, setAddRole] = useState<ProjectRole>("write")

  useEffect(() => {
    usersApi.list().then((users) => setAvailable(users.map((u) => u.username))).catch(() => {})
  }, [])

  async function add() {
    if (!adding) return
    try {
      const updated = await projectsApi.addMember(project.id, adding, addRole)
      onChange(updated)
      setAdding("")
      setAddRole("write")
    } catch (e) {
      alert(e instanceof Error ? e.message : tCommon("status.error"))
    }
  }

  async function changeRole(username: string, role: ProjectRole) {
    try {
      const updated = await projectsApi.setMemberRole(project.id, username, role)
      onChange(updated)
    } catch (e) {
      alert(e instanceof Error ? e.message : tCommon("status.error"))
    }
  }

  async function remove(username: string) {
    if (!confirm(t("members.remove_confirm", { username }))) return
    const updated = await projectsApi.removeMember(project.id, username)
    onChange(updated)
  }

  const memberNames = project.members.map((m) => m.username)
  const candidates = available.filter((u) => !memberNames.includes(u))

  function roleLabel(role: ProjectRole) {
    return t(`members.roles.${role}`, { defaultValue: role })
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-1.5">
        {project.members.length === 0 && (
          <p className="text-xs text-zinc-600">{t("members.no_members")}</p>
        )}
        {project.members.map((m) => (
          <div
            key={m.username}
            className={`inline-flex items-center gap-2 pl-2.5 pr-1 py-1 rounded-md border text-xs ${ROLE_STYLE[m.role]}`}
          >
            <span className="font-medium">{m.username}</span>
            <select
              value={m.role}
              onChange={(e) => changeRole(m.username, e.target.value as ProjectRole)}
              className="ml-auto px-1.5 py-0.5 rounded bg-zinc-900/60 border border-white/10 text-[11px] text-zinc-200"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>{roleLabel(r)}</option>
              ))}
            </select>
            <button
              onClick={() => remove(m.username)}
              className="p-0.5 rounded hover:bg-rose-500/20 hover:text-rose-300 transition-colors"
            >
              <X size={11} />
            </button>
          </div>
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
          <select
            value={addRole}
            onChange={(e) => setAddRole(e.target.value as ProjectRole)}
            className="px-2 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{roleLabel(r)}</option>
            ))}
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
