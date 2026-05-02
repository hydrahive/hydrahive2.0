/**
 * Strukturierte Card für shell_exec-Tool-Results.
 * Erwartet content als JSON-String mit {exit_code, stdout, stderr, timed_out?}.
 * Fallback: Pre-Block wenn JSON nicht parsebar.
 */
import { useState } from "react"
import { ChevronDown, ChevronRight, Terminal } from "lucide-react"

interface ShellOutput {
  exit_code?: number
  stdout?: string
  stderr?: string
  timed_out?: boolean
}

function tryParse(content: string): ShellOutput | null {
  try {
    const data = JSON.parse(content)
    if (typeof data === "object" && data !== null && "exit_code" in data) return data
  } catch {
    /* fall through */
  }
  return null
}

export function ShellExecCard({ content, isError }: { content: string; isError?: boolean }) {
  const data = tryParse(content)
  if (!data) return null

  const code = data.exit_code ?? -1
  const ok = code === 0 && !isError && !data.timed_out
  const stdout = (data.stdout ?? "").trim()
  const stderr = (data.stderr ?? "").trim()

  return (
    <div className="rounded-lg border border-zinc-700/40 bg-zinc-900/40 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/60 border-b border-zinc-700/40">
        <Terminal size={11} className="text-zinc-500" />
        <span className="text-[10.5px] font-mono text-zinc-400">shell_exec</span>
        <span className={`ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono
          ${ok ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`}>
          exit {code}
          {data.timed_out && " · timeout"}
        </span>
      </div>
      <Section label="stdout" text={stdout} muted={!stdout} />
      {stderr && <Section label="stderr" text={stderr} dim />}
    </div>
  )
}

function Section({ label, text, muted, dim }: {
  label: string; text: string; muted?: boolean; dim?: boolean
}) {
  const [open, setOpen] = useState(text.length > 0 && text.split("\n").length <= 20)
  if (!text) {
    return (
      <div className="px-3 py-1.5 text-[10.5px] text-zinc-600 font-mono italic">
        {label}: <span className="opacity-60">leer</span>
      </div>
    )
  }
  const lines = text.split("\n").length
  const preview = lines > 20 || text.length > 600
  return (
    <div className={`border-t border-zinc-800/40 ${dim ? "bg-rose-950/10" : ""}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-1.5 px-3 py-1 text-left text-[10.5px] font-mono text-zinc-500 hover:text-zinc-300 hover:bg-white/[3%]"
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        <span>{label}</span>
        {preview && <span className="text-zinc-600">· {lines} Zeilen, {text.length} chars</span>}
      </button>
      {open && (
        <pre className={`px-3 pb-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap
          ${dim ? "text-rose-200/80" : "text-zinc-300"} ${muted ? "opacity-60" : ""}`}>
          {text}
        </pre>
      )}
    </div>
  )
}
