import { useTranslation } from "react-i18next"
import { Download } from "lucide-react"
import type { Episode, ScrapeResult } from "./types"

interface Props {
  result: ScrapeResult
  selected: Set<string>
  onToggle: (key: string) => void
  onSelectAll: () => void
  onClearAll: () => void
  onDownload: () => void
  downloading: boolean
}

export function EpisodeList({
  result, selected, onToggle, onSelectAll, onClearAll, onDownload, downloading
}: Props) {
  const { t } = useTranslation("streaming")
  const allSelected = selected.size === result.episodes.length

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/60 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div>
          <div className="text-sm font-medium text-zinc-100">{result.title}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">
            Staffel {result.season} · {result.episodes.length} Folgen
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={allSelected ? onClearAll : onSelectAll}
            className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            {allSelected ? t("deselect_all") : t("select_all")}
          </button>
          <button
            onClick={onDownload}
            disabled={selected.size === 0 || downloading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors"
          >
            <Download size={12} />
            {downloading ? t("starting") : t("download", { count: selected.size })}
          </button>
        </div>
      </div>

      <div className="divide-y divide-white/[4%]">
        {result.episodes.map((ep: Episode) => (
          <label
            key={ep.key}
            className="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-white/[2%] transition-colors"
          >
            <input
              type="checkbox"
              checked={selected.has(ep.key)}
              onChange={() => onToggle(ep.key)}
              className="w-4 h-4 accent-violet-500 flex-shrink-0"
            />
            <span className="text-xs text-zinc-400 w-10 flex-shrink-0 font-mono">
              E{String(ep.episode).padStart(2, "0")}
            </span>
            <span className="text-xs text-zinc-300 truncate">{ep.key.replace(/-/g, " ")}</span>
            <span className="ml-auto text-[10px] text-zinc-600 font-mono">{ep.bunny_video_type}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
