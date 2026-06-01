import { useState } from "react"
import { GitBranch, FileJson, ScrollText } from "lucide-react"
import { dataminingApi } from "./api"

type Source = "git" | "jsonl" | "logs"
type State = "idle" | "running" | "done" | "error"

const SOURCES: { key: Source; label: string; icon: typeof GitBranch; run: () => Promise<unknown> }[] = [
  { key: "git", label: "Git-Log", icon: GitBranch, run: () => dataminingApi.startGitImport() },
  { key: "jsonl", label: "JSONL", icon: FileJson, run: () => dataminingApi.startJsonlImport() },
  { key: "logs", label: "Logs", icon: ScrollText, run: () => dataminingApi.startLogsImport() },
]

/**
 * Ein-Klick-Import der Datamining-Zusatzquellen (git/jsonl/logs) mit Backend-
 * Defaults. Self-contained — hält den Status pro Quelle selbst (#190).
 */
export function SourceImportButtons() {
  const [state, setState] = useState<Record<Source, State>>({ git: "idle", jsonl: "idle", logs: "idle" })

  async function run(s: Source, fn: () => Promise<unknown>) {
    setState((prev) => ({ ...prev, [s]: "running" }))
    try {
      await fn()
      setState((prev) => ({ ...prev, [s]: "done" }))
    } catch {
      setState((prev) => ({ ...prev, [s]: "error" }))
    }
  }

  const baseClass = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-50"

  return (
    <>
      {SOURCES.map(({ key, label, icon: Icon, run: fn }) => {
        const st = state[key]
        return (
          <button
            key={key}
            onClick={() => run(key, fn)}
            disabled={st === "running"}
            className={baseClass}
            title={`Datamining-Import: ${label} (Backend-Defaults)`}
          >
            <Icon size={12} />
            {label}
            {st === "running" && <span className="text-amber-300 animate-pulse">…</span>}
            {st === "done" && <span className="text-emerald-400">✓</span>}
            {st === "error" && <span className="text-red-400">✗</span>}
          </button>
        )
      })}
    </>
  )
}
