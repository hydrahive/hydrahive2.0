import { Film, Loader2 } from "lucide-react"
import type { ExportStatus } from "./useCutExport"

interface Props {
  status: ExportStatus
  error: string | null
  disabled: boolean
  onExport: () => void
}

/** Export-Auslöser: rendert den Schnitt (FFmpeg). Die fertigen Filme erscheinen
 *  in der „Fertige Filme"-Box (ExportLibrary). */
export function ExportBar({ status, error, disabled, onExport }: Props) {
  const running = status === "running"
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#2a364b] pt-3">
      <button
        type="button"
        onClick={onExport}
        disabled={disabled || running}
        className="inline-flex items-center gap-1.5 rounded-[4px] border border-emerald-500/50 bg-emerald-500/10 px-3 py-1.5 text-[12px] font-semibold text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:opacity-40"
      >
        {running ? <Loader2 size={14} className="animate-spin" /> : <Film size={14} />}
        {running ? "Rendere…" : "Film exportieren"}
      </button>
      {running ? <span className="text-[11px] text-[#8d9ab0]">Das kann je nach Länge einen Moment dauern…</span> : null}
      {status === "done" ? <span className="text-[11px] text-emerald-300">Fertig — siehe „Fertige Filme".</span> : null}
      {status === "error" ? <span className="text-[11px] text-rose-300">{error}</span> : null}
    </div>
  )
}
