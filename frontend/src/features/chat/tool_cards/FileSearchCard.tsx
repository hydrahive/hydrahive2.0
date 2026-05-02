/**
 * Strukturierte Card für file_search-Tool-Results.
 * Erwartet content als JSON mit {hits: [{path, matches?: [{line, text}]}], count, truncated}.
 */
import { Search } from "lucide-react"

interface FileMatch { line: number; text: string }
interface FileHit { path: string; matches?: FileMatch[] }
interface FileSearchOutput {
  hits?: FileHit[]
  count?: number
  truncated?: boolean
}

function tryParse(content: string): FileSearchOutput | null {
  try {
    const data = JSON.parse(content)
    if (data && typeof data === "object" && Array.isArray(data.hits)) return data
  } catch {
    /* fall through */
  }
  return null
}

export function FileSearchCard({ content }: { content: string }) {
  const data = tryParse(content)
  if (!data || !data.hits) return null

  return (
    <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/[4%] overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/[8%] border-b border-emerald-500/15">
        <Search size={11} className="text-emerald-400" />
        <span className="text-[10.5px] font-mono text-emerald-300">file_search</span>
        <span className="ml-auto text-[10px] text-emerald-400/60 tabular-nums">
          {data.count ?? data.hits.length} {data.truncated ? "+" : ""}
        </span>
      </div>
      {data.hits.length === 0 ? (
        <div className="px-3 py-2 text-[11px] text-zinc-500 italic">Keine Treffer.</div>
      ) : (
        <ul className="divide-y divide-emerald-500/10 max-h-72 overflow-y-auto">
          {data.hits.map((h, i) => (
            <li key={i} className="px-3 py-1.5">
              <div className="text-[11px] font-mono text-emerald-200 truncate">{h.path}</div>
              {h.matches && h.matches.length > 0 && (
                <ul className="mt-0.5 space-y-0.5">
                  {h.matches.slice(0, 5).map((m, j) => (
                    <li key={j} className="text-[10.5px] font-mono text-zinc-400 truncate">
                      <span className="text-zinc-600 mr-2 tabular-nums">{m.line}:</span>
                      {m.text}
                    </li>
                  ))}
                  {h.matches.length > 5 && (
                    <li className="text-[10px] text-zinc-600 italic pl-7">
                      … {h.matches.length - 5} weitere
                    </li>
                  )}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
