import { Edit2, ExternalLink, Link2, Trash2 } from "lucide-react"
import type { WikiPage } from "./types"

interface Props {
  page: WikiPage
  onEdit: () => void
  onDelete: () => void
  onNavigate: (slug: string) => void
}

function renderBody(body: string, onNavigate: (slug: string) => void): React.ReactNode[] {
  const parts = body.split(/(\[\[[^\]]+\]\])/g)
  return parts.map((part, i) => {
    const m = part.match(/^\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]$/)
    if (m) {
      const slug = m[1].trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
      const label = m[2] || m[1]
      return (
        <button
          key={i}
          onClick={() => onNavigate(slug)}
          className="text-violet-400 hover:text-violet-300 underline decoration-dotted"
        >
          {label}
        </button>
      )
    }
    return <span key={i} style={{ whiteSpace: "pre-wrap" }}>{part}</span>
  })
}

export function PageDetail({ page, onEdit, onDelete, onNavigate }: Props) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-start gap-3 p-4 border-b border-white/[6%]">
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold text-zinc-100 truncate">{page.title}</h1>
          <div className="flex items-center gap-3 mt-1 text-[10px] text-zinc-500">
            <span>{page.author}</span>
            {page.updated_at && <span>{new Date(page.updated_at).toLocaleDateString("de")}</span>}
            {page.source_url && (
              <a href={page.source_url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1 text-violet-500 hover:text-violet-300">
                <ExternalLink size={10} /> Quelle
              </a>
            )}
          </div>
        </div>
        <div className="flex gap-1 shrink-0">
          <button onClick={onEdit}
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]">
            <Edit2 size={14} />
          </button>
          <button onClick={onDelete}
            className="p-1.5 rounded-md text-zinc-400 hover:text-red-400 hover:bg-red-500/10">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Tags + Entities */}
      {(page.tags.length > 0 || page.entities.length > 0) && (
        <div className="flex flex-wrap gap-1.5 px-4 py-2 border-b border-white/[4%]">
          {page.tags.map((t) => (
            <span key={t} className="text-[10px] bg-violet-600/20 text-violet-300 px-2 py-0.5 rounded-full">{t}</span>
          ))}
          {page.entities.map((e) => (
            <span key={e} className="text-[10px] bg-zinc-700/60 text-zinc-300 px-2 py-0.5 rounded-full">{e}</span>
          ))}
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 text-sm text-zinc-300 leading-relaxed">
        {renderBody(page.body, onNavigate)}
      </div>

      {/* Backlinks */}
      {page.backlinks.length > 0 && (
        <div className="px-4 py-3 border-t border-white/[6%]">
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-500 mb-1.5">
            <Link2 size={10} /> Verlinkt von
          </div>
          <div className="flex flex-wrap gap-1.5">
            {page.backlinks.map((s) => (
              <button key={s} onClick={() => onNavigate(s)}
                className="text-[10px] text-violet-400 hover:text-violet-200 bg-violet-600/10 px-2 py-0.5 rounded-full">
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
