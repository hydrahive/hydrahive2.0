import { Trash2 } from "lucide-react"
import type { ImportJob } from "./types"
import { formatBytes, formatRelative } from "./format"

interface Props { job: ImportJob; onDelete: () => void }

const STATUS_CLS: Record<ImportJob["status"], string> = {
  queued:  "bg-zinc-500/15 text-zinc-300 ring-zinc-500/30",
  running: "bg-amber-500/15 text-amber-300 ring-amber-500/30 animate-pulse",
  done:    "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  failed:  "bg-rose-500/15 text-rose-300 ring-rose-500/30",
}

export function ImportJobCard({ job, onDelete }: Props) {
  const target = job.target_qcow2.split("/").pop() ?? job.target_qcow2
  const source = job.source_path.split("/").pop() ?? job.source_path
  return (
    <div className="rounded-lg border border-white/[8%] bg-white/[2%] p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-mono text-zinc-300 truncate">{source}</p>
          <p className="text-[10px] text-zinc-500 truncate">→ {target}</p>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[11px] ring-1 ${STATUS_CLS[job.status]}`}>{job.status}</span>
      </div>
      {job.status === "running" && (
        <div className="space-y-1">
          <div className="h-1 rounded-full bg-zinc-800 overflow-hidden">
            <div className="h-full bg-violet-500 transition-all" style={{ width: `${job.progress_pct}%` }} />
          </div>
          <p className="text-[10px] text-zinc-500 text-right">{job.progress_pct}%</p>
        </div>
      )}
      {job.error_code && <p className="text-[11px] text-rose-300">{job.error_code}</p>}
      <div className="flex items-center justify-between text-[10px] text-zinc-500">
        <span>{formatRelative(job.created_at)} · {formatBytes(job.bytes_total)}</span>
        {job.status !== "running" && (
          <button onClick={onDelete} className="p-1 rounded text-zinc-500 hover:text-rose-300 hover:bg-rose-500/10">
            <Trash2 size={11} />
          </button>
        )}
      </div>
    </div>
  )
}
