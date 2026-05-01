import { useState } from "react"
import { Eye, EyeOff, Loader2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"

interface Props {
  projectId: string
  existingNames: string[]
  onCancel: () => void
  onAdded: () => void | Promise<void>
}

const NAME_RE = /^[a-z0-9][a-z0-9_-]{0,49}$/

export function AddRepoForm({ projectId, existingNames, onCancel, onAdded }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [name, setName] = useState("")
  const [url, setUrl] = useState("")
  const [branch, setBranch] = useState("")
  const [token, setToken] = useState("")
  const [showToken, setShowToken] = useState(false)
  const [busy, setBusy] = useState<"" | "clone" | "init">("")
  const [error, setError] = useState<string | null>(null)

  const nameOk = NAME_RE.test(name) && !existingNames.includes(name) && name !== "_root"
  const canClone = nameOk && url.trim().length > 0 && busy === ""
  const canInit = nameOk && busy === ""

  async function run(b: "clone" | "init") {
    setBusy(b); setError(null)
    try {
      if (b === "clone") {
        await projectsApi.cloneRepo(projectId, {
          name, url, branch: branch || undefined, token: token || undefined,
        })
      } else {
        await projectsApi.initRepo(projectId, name)
      }
      await onAdded()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy("") }
  }

  return (
    <div className="rounded-lg border border-violet-500/20 bg-violet-500/[3%] p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-violet-300 font-medium">{t("git.add_repo_title")}</p>
        <button onClick={onCancel} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
          <X size={12} />
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.repo_name")}</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            placeholder="my-repo"
            className={`w-full px-2 py-1 rounded-md bg-zinc-900 border text-xs text-zinc-200 font-mono ${
              name && !nameOk ? "border-rose-500/40" : "border-white/[8%]"
            }`} />
          {name && !nameOk && (
            <p className="text-[10px] text-rose-400">{t("git.repo_name_invalid")}</p>
          )}
        </div>
        <div className="sm:col-span-2 space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.clone_url")}</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo.git"
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.branch_optional")}</label>
          <input value={branch} onChange={(e) => setBranch(e.target.value)}
            placeholder="main"
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </div>
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("git.token")}</label>
          <div className="flex gap-1">
            <input type={showToken ? "text" : "password"} value={token} onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_…"
              className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono" />
            <button type="button" onClick={() => setShowToken(!showToken)}
              className="px-2 py-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
              {showToken ? <EyeOff size={12} /> : <Eye size={12} />}
            </button>
          </div>
        </div>
      </div>
      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-2 py-1">{error}</p>
      )}
      <div className="flex justify-end gap-2 pt-1">
        <button onClick={() => run("init")} disabled={!canInit}
          className="px-3 py-1 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-white/[8%] disabled:opacity-30">
          {busy === "init" ? <Loader2 size={11} className="animate-spin" /> : t("git.init_empty")}
        </button>
        <button onClick={() => run("clone")} disabled={!canClone}
          className="px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
          {busy === "clone" ? <Loader2 size={11} className="animate-spin" /> : t("git.clone")}
        </button>
      </div>
    </div>
  )
}
