import { Download, Film, Loader2 } from "lucide-react"
import { timecode } from "./useCutPlayback"
import { useCutExport } from "./useCutExport"

interface Props {
  projectId: string
  disabled: boolean
}

/** Export-Leiste: rendert den Schnitt (FFmpeg) und bietet den Download an. */
export function ExportBar({ projectId, disabled }: Props) {
  const { status, result, error, run } = useCutExport(projectId)
  const running = status === "running"

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#2a364b] pt-3">
      <button
        type="button"
        onClick={() => void run()}
        disabled={disabled || running}
        className="inline-flex items-center gap-1.5 rounded-[4px] border border-emerald-500/50 bg-emerald-500/10 px-3 py-1.5 text-[12px] font-semibold text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:opacity-40"
      >
        {running ? <Loader2 size={14} className="animate-spin" /> : <Film size={14} />}
        {running ? "Rendere…" : "Film exportieren"}
      </button>

      {status === "done" && result ? (
        <a
          href={result.downloadUrl}
          download="schnitt.mp4"
          className="inline-flex items-center gap-1.5 rounded-[4px] border border-cyan-400/50 bg-cyan-400/10 px-3 py-1.5 text-[12px] font-semibold text-cyan-100 transition-colors hover:bg-cyan-400/20"
        >
          <Download size={14} /> Download ({timecode(result.duration)})
        </a>
      ) : null}

      {running ? (
        <span className="text-[11px] text-[#8d9ab0]">Das kann je nach Länge einen Moment dauern…</span>
      ) : null}

      {status === "error" ? <span className="text-[11px] text-rose-300">{error}</span> : null}
    </div>
  )
}
