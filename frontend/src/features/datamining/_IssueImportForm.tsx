import { useState } from "react"
import { GitPullRequest } from "lucide-react"
import { dataminingApi } from "./api"

type Variant = "github" | "gitea"
type State = "idle" | "running" | "done" | "error"


export function IssueImportButtons({
  active, onToggle,
}: {
  active: Variant | null
  onToggle: (v: Variant) => void
}) {
  const baseClass = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
  return (
    <>
      <button
        onClick={() => onToggle("github")}
        className={`${baseClass} ${active === "github" ? "bg-zinc-700 text-zinc-200" : "bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200"}`}
      >
        <GitPullRequest size={12} />
        GitHub Issues
      </button>
      <button
        onClick={() => onToggle("gitea")}
        className={`${baseClass} ${active === "gitea" ? "bg-zinc-700 text-zinc-200" : "bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200"}`}
      >
        <GitPullRequest size={12} />
        Gitea Issues
      </button>
    </>
  )
}


export function IssueImportForm({ variant }: { variant: Variant }) {
  const [owner, setOwner] = useState("")
  const [repo, setRepo] = useState("")
  const [token, setToken] = useState("")
  const [baseUrl, setBaseUrl] = useState("http://192.168.3.22:3001")
  const [state, setState] = useState<State>("idle")
  const [result, setResult] = useState<string | null>(null)

  async function run() {
    if (!owner || !repo) return
    setState("running"); setResult(null)
    try {
      const res = variant === "github"
        ? await dataminingApi.importGithub(owner, repo, token)
        : await dataminingApi.importGitea(owner, repo, baseUrl, token)
      setState("done")
      setResult(`${res.inserted} Events importiert`)
    } catch {
      setState("error"); setResult("Import fehlgeschlagen")
    }
  }

  const inputClass = "px-2 py-1 rounded text-xs bg-zinc-800 text-zinc-200 border border-white/[8%] focus:outline-none focus:border-amber-400/50"

  return (
    <div className="flex flex-wrap items-end gap-2 p-3 rounded-lg bg-white/[3%] border border-white/[6%]">
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Owner</label>
        <input
          value={owner} onChange={e => setOwner(e.target.value)}
          placeholder="z.B. hydrahive"
          className={`${inputClass} w-32`}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Repo</label>
        <input
          value={repo} onChange={e => setRepo(e.target.value)}
          placeholder="z.B. hydrahive2.0"
          className={`${inputClass} w-36`}
        />
      </div>
      {variant === "gitea" && (
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500">Base-URL</label>
          <input
            value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
            className={`${inputClass} w-52`}
          />
        </div>
      )}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Token (optional)</label>
        <input
          type="password" value={token} onChange={e => setToken(e.target.value)}
          placeholder="token…"
          className={`${inputClass} w-36`}
        />
      </div>
      <button
        onClick={run}
        disabled={state === "running" || !owner || !repo}
        className="px-3 py-1.5 rounded text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 disabled:opacity-40 transition-colors"
      >
        {state === "running" ? "lädt…" : "Importieren"}
      </button>
      {result && (
        <span className={`text-xs ${state === "done" ? "text-emerald-400" : "text-red-400"}`}>
          {result}
        </span>
      )}
    </div>
  )
}
