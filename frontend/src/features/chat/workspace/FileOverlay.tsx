import { useEffect } from "react"
import { useTranslation } from "react-i18next"
import { X } from "lucide-react"
import { FileEditor } from "./FileEditor"
import { MediaViewer } from "./MediaViewer"
import { useWorkspace } from "./useWorkspace"
import type { FileKind } from "./fileType"

interface Props {
  agentId: string
  path: string
  kind: FileKind
  onClose: () => void
}

export function FileOverlay({ agentId, path, kind, onClose }: Props) {
  const { t } = useTranslation("workspace")
  const ws = useWorkspace(agentId)

  useEffect(() => {
    if (kind === "text") ws.open(path)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, path, kind])

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") onClose() }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 md:p-8"
      onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-5xl h-[85vh] rounded-2xl border border-white/10 bg-zinc-900 shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[8%] bg-black/30">
          <span className="text-xs text-zinc-300 truncate flex-1 font-mono">{path}</span>
          <button onClick={onClose} title={t("close")}
            className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 min-h-0">
          {kind === "text" && ws.openFile && <FileEditor file={ws.openFile} onSave={ws.save} />}
          {kind === "text" && !ws.openFile && (
            <div className="p-3 text-[11px] text-zinc-600">{ws.error ?? t("loading")}</div>
          )}
          {kind !== "text" && <MediaViewer agentId={agentId} path={path} kind={kind} />}
        </div>
      </div>
    </div>
  )
}
