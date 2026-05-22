import { CheckCircle, Clock, Download, XCircle, SkipForward } from "lucide-react"
import type { StreamingJob } from "./types"

interface Props {
  jobs: StreamingJob[]
}

const STATUS_ICON = {
  pending:     <Clock size={13} className="text-zinc-500" />,
  downloading: <Download size={13} className="text-violet-400 animate-pulse" />,
  done:        <CheckCircle size={13} className="text-emerald-400" />,
  error:       <XCircle size={13} className="text-rose-400" />,
  skipped:     <SkipForward size={13} className="text-zinc-500" />,
} as const

export function JobList({ jobs }: Props) {
  if (jobs.length === 0) return null

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/60 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-white/5">
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-widest">Downloads</span>
      </div>
      <div className="divide-y divide-white/[4%]">
        {jobs.map(job => (
          <div key={job.id} className="px-4 py-2.5 flex items-center gap-3">
            {STATUS_ICON[job.status] ?? STATUS_ICON.pending}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-300 truncate">{job.series_title}</span>
                <span className="text-[10px] text-zinc-500 font-mono flex-shrink-0">
                  S{String(job.season).padStart(2, "0")}E{String(job.episode).padStart(2, "0")}
                </span>
              </div>
              {job.status === "downloading" && (
                <div className="mt-1 h-1 rounded-full bg-zinc-800 overflow-hidden w-full">
                  <div
                    className="h-full bg-violet-500 transition-all duration-500"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              )}
              {job.error && (
                <div className="text-[10px] text-rose-400 mt-0.5 truncate">{job.error}</div>
              )}
            </div>
            <span className="text-[10px] text-zinc-600 flex-shrink-0">
              {job.status === "downloading" ? `${job.progress}%` : job.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
