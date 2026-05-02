import { useState } from "react"
import { Download, Plus, Search } from "lucide-react"
import type { WikiPage } from "./types"

interface Props {
  pages: WikiPage[]
  selected: string | null
  onSelect: (slug: string) => void
  onNew: () => void
  onIngest: () => void
  onSearch: (q: string) => void
}

export function PageList({ pages, selected, onSelect, onNew, onIngest, onSearch }: Props) {
  const [q, setQ] = useState("")

  function handleSearch(val: string) {
    setQ(val)
    onSearch(val)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-3 border-b border-white/[6%]">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            value={q}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Suchen…"
            className="w-full bg-white/[4%] border border-white/[8%] rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50"
          />
        </div>
        <button
          onClick={onIngest}
          className="p-1.5 rounded-md bg-zinc-700/60 text-zinc-300 hover:bg-zinc-600/60 transition-colors"
          title="URL / Text aufnehmen"
        >
          <Download size={14} />
        </button>
        <button
          onClick={onNew}
          className="p-1.5 rounded-md bg-violet-600/20 text-violet-300 hover:bg-violet-600/40 transition-colors"
          title="Neue Seite"
        >
          <Plus size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {pages.length === 0 && (
          <p className="text-xs text-zinc-600 text-center mt-8">Keine Seiten.</p>
        )}
        {pages.map((p) => (
          <button
            key={p.slug}
            onClick={() => onSelect(p.slug)}
            className={`w-full text-left px-3 py-2.5 border-b border-white/[4%] transition-colors ${
              selected === p.slug
                ? "bg-violet-600/20 text-violet-200"
                : "text-zinc-300 hover:bg-white/[4%]"
            }`}
          >
            <div className="text-xs font-medium truncate">{p.title}</div>
            {p.snippet && (
              <div
                className="text-[10px] text-zinc-500 mt-0.5 truncate"
                dangerouslySetInnerHTML={{ __html: p.snippet }}
              />
            )}
            {p.tags.length > 0 && !p.snippet && (
              <div className="flex gap-1 mt-1 flex-wrap">
                {p.tags.slice(0, 3).map((t) => (
                  <span key={t} className="text-[9px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded-full">{t}</span>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
