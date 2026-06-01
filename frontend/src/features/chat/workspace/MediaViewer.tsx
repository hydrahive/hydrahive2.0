import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Download } from "lucide-react"
import { workspaceApi } from "./api"
import type { FileKind } from "./fileType"

interface Props { agentId: string; path: string; kind: Exclude<FileKind, "text"> }

export function MediaViewer({ agentId, path, kind }: Props) {
  const { t } = useTranslation("workspace")
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const name = path.split("/").pop() ?? path

  useEffect(() => {
    let revoke: string | null = null
    let alive = true
    setUrl(null); setError(false)
    workspaceApi.rawObjectUrl(agentId, path)
      .then((u) => { if (alive) { setUrl(u); revoke = u } else { URL.revokeObjectURL(u) } })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false; if (revoke) URL.revokeObjectURL(revoke) }
  }, [agentId, path])

  if (error) return <div className="p-3 text-[11px] text-rose-400">{t("loading")} ✗</div>
  if (!url) return <div className="p-3 text-[11px] text-zinc-600">{t("loading")}</div>

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-2 py-1 border-b border-white/[6%]">
        <span className="text-[10px] text-zinc-400 truncate flex-1 font-mono">{path}</span>
        <a href={url} download={name}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-violet-500/15 text-violet-300 hover:bg-violet-500/25">
          <Download size={10} /> {name}
        </a>
      </div>
      <div className="flex-1 min-h-0 overflow-auto flex items-center justify-center p-3">
        {kind === "image" && <img src={url} alt={name} className="max-w-full max-h-full object-contain" />}
        {kind === "video" && <video src={url} controls className="max-w-full max-h-full" />}
        {kind === "audio" && <audio src={url} controls className="w-full" />}
        {kind === "download" && (
          <a href={url} download={name}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs">
            <Download size={14} /> {name}
          </a>
        )}
      </div>
    </div>
  )
}
