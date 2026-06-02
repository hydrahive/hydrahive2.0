import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { CheckCircle, Clock, Download, Trash2, X, XCircle, SkipForward } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import type { StreamingJob } from "./types"
import { streamingApi } from "./api"

interface Props {
  jobs: StreamingJob[]
  onDeleted: () => void
}

const STATUS_ICON = {
  pending:     <Clock size={13} className="text-zinc-500" />,
  downloading: <Download size={13} className="text-violet-400 animate-pulse" />,
  done:        <CheckCircle size={13} className="text-emerald-400" />,
  error:       <XCircle size={13} className="text-rose-400" />,
  skipped:     <SkipForward size={13} className="text-zinc-500" />,
} as const

const DELETABLE = new Set(["done", "error", "skipped"])
const CANCELLABLE = new Set(["pending", "downloading"])

export function JobList({ jobs, onDeleted }: Props) {
  const { t } = useTranslation("streaming")
  if (jobs.length === 0) return null

  async function deleteJob(id: string) {
    await streamingApi.deleteJob(id)
    onDeleted()
  }

  async function cancelJob(id: string) {
    await streamingApi.cancelJob(id)
    onDeleted()
  }

  async function deleteFinished() {
    const finished = jobs.filter(j => DELETABLE.has(j.status))
    await Promise.all(finished.map(j => streamingApi.deleteJob(j.id)))
    onDeleted()
  }

  const hasFinished = jobs.some(j => DELETABLE.has(j.status))

  return (
    <div className="box overflow-hidden" style={{ "--c": rgbFor("/llm") } as CSSProperties}>
      <div className="px-4 py-2.5 border-b border-white/5 flex items-center">
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-widest flex-1">Downloads</span>
        {hasFinished && (
          <button
            onClick={deleteFinished}
            className="text-[10px] text-zinc-600 hover:text-rose-400 transition-colors flex items-center gap-1"
          >
            <Trash2 size={11} />
            Fertige löschen
          </button>
        )}
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
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-[10px] text-zinc-600">
                {job.status === "downloading" ? `${job.progress}%` : job.status}
              </span>
              {CANCELLABLE.has(job.status) && (
                <button
                  onClick={() => cancelJob(job.id)}
                  className="text-zinc-700 hover:text-amber-400 transition-colors"
                  title={t("cancel")}
                >
                  <X size={12} />
                </button>
              )}
              {DELETABLE.has(job.status) && (
                <button
                  onClick={() => deleteJob(job.id)}
                  className="text-zinc-700 hover:text-rose-400 transition-colors"
                  title={t("delete")}
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
