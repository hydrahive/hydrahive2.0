/**
 * Strukturierte Card für git_diff (plugin__git-stats__git_diff).
 * Erwartet content als JSON mit {repo, ref, ref2?, stat, diff}.
 * Diff-Zeilen werden mit +/- color-coded.
 */
import { useState } from "react"
import { ChevronDown, ChevronRight, GitCompare } from "lucide-react"

interface DiffOutput {
  repo?: string
  ref?: string
  ref2?: string | null
  file?: string | null
  stat?: string
  diff?: string
}

function tryParse(content: string): DiffOutput | null {
  try {
    const data = JSON.parse(content)
    if (data && typeof data === "object" && typeof data.diff === "string") return data
  } catch {
    /* fall through */
  }
  return null
}

function lineClass(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---")) return "text-zinc-500"
  if (line.startsWith("@@")) return "text-violet-300 bg-violet-500/[6%]"
  if (line.startsWith("+")) return "text-emerald-300 bg-emerald-500/[5%]"
  if (line.startsWith("-")) return "text-rose-300 bg-rose-500/[5%]"
  return "text-zinc-400"
}

export function GitDiffCard({ content }: { content: string }) {
  const data = tryParse(content)
  const [open, setOpen] = useState(true)
  if (!data) return null

  const range = data.ref2 ? `${data.ref}…${data.ref2}` : (data.ref ?? "HEAD")
  const diffLines = (data.diff ?? "").split("\n")

  return (
    <div className="rounded-lg border border-violet-500/20 bg-violet-500/[3%] overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-violet-500/[8%] border-b border-violet-500/15">
        <GitCompare size={11} className="text-violet-400" />
        <span className="text-[10.5px] font-mono text-violet-300">git_diff</span>
        <span className="text-[10.5px] font-mono text-zinc-400 truncate">{range}</span>
        {data.file && <span className="text-[10px] text-zinc-500 truncate">· {data.file}</span>}
      </div>
      {data.stat && (
        <pre className="px-3 py-1 text-[10.5px] font-mono text-zinc-400 border-b border-violet-500/10 whitespace-pre-wrap">
          {data.stat}
        </pre>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-1.5 px-3 py-1 text-left text-[10.5px] font-mono text-zinc-500 hover:text-zinc-300 hover:bg-white/[3%]"
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        <span>diff · {diffLines.length} Zeilen</span>
      </button>
      {open && (
        <div className="text-[11px] font-mono overflow-x-auto max-h-96 overflow-y-auto">
          {diffLines.map((line, i) => (
            <div key={i} className={`px-3 ${lineClass(line)} whitespace-pre`}>
              {line || " "}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
