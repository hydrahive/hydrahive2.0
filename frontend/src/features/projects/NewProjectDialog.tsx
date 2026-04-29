import { useEffect, useState } from "react"
import { GitBranch, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { llmInfoApi } from "@/features/agents/api"
import { projectsApi, usersApi } from "./api"

interface Props {
  onClose: () => void
  onCreated: (id: string) => void
}

export function NewProjectDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [model, setModel] = useState("")
  const [models, setModels] = useState<string[]>([])
  const [users, setUsers] = useState<string[]>([])
  const [members, setMembers] = useState<string[]>([])
  const [initGit, setInitGit] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    llmInfoApi.getModels().then((info) => {
      setModels(info.models)
      setModel(info.default_model || info.models[0] || "")
    }).catch(() => {})
    usersApi.list().then((us) => setUsers(us.map((u) => u.username))).catch(() => {})
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const created = await projectsApi.create({
        name: name.trim(), description, members, llm_model: model, init_git: initGit,
      })
      onCreated(created.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  function toggleMember(u: string) {
    setMembers((cur) => cur.includes(u) ? cur.filter((m) => m !== u) : [...cur, u])
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{t("new_dialog.title")}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{tCommon("labels.name")}</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required
            placeholder={t("new_dialog.name_placeholder")}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm" />
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{tCommon("labels.description")} (optional)</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm leading-relaxed" />
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{t("new_dialog.model_label")}</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
            {models.length === 0 && <option value="">{t("new_dialog.no_model")}</option>}
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{tCommon("labels.members")}</label>
          <div className="flex flex-wrap gap-1.5 px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] min-h-[40px]">
            {users.length === 0 && <p className="text-xs text-zinc-600">{t("new_dialog.no_users")}</p>}
            {users.map((u) => {
              const sel = members.includes(u)
              return (
                <button key={u} type="button" onClick={() => toggleMember(u)}
                  className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
                    sel ? "bg-violet-500/[15%] border border-violet-500/40 text-violet-200"
                        : "bg-white/[3%] border border-white/[6%] text-zinc-400 hover:text-zinc-200"
                  }`}>{u}</button>
              )
            })}
          </div>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={initGit} onChange={(e) => setInitGit(e.target.checked)}
            className="w-4 h-4 accent-violet-600" />
          <span className="text-sm text-zinc-300 inline-flex items-center gap-1.5">
            <GitBranch size={13} className="text-zinc-500" /> {t("new_dialog.git_init")}
          </span>
        </label>

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">{tCommon("actions.cancel")}</button>
          <button type="submit" disabled={busy || !name.trim() || !model}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
            {tCommon("actions.create")}
          </button>
        </div>
      </form>
    </div>
  )
}
