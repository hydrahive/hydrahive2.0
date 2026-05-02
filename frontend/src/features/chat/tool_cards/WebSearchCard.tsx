/**
 * Strukturierte Card für web_search-Tool-Results.
 * Erwartet content als JSON mit {query, results: [{title, url, snippet}], count}.
 */
import { Globe } from "lucide-react"

interface WebResult {
  title: string
  url: string
  snippet: string
}

interface WebOutput {
  query?: string
  results?: WebResult[]
  count?: number
}

function tryParse(content: string): WebOutput | null {
  try {
    const data = JSON.parse(content)
    if (data && typeof data === "object" && Array.isArray(data.results)) return data
  } catch {
    /* fall through */
  }
  return null
}

export function WebSearchCard({ content }: { content: string }) {
  const data = tryParse(content)
  if (!data || !data.results) return null

  return (
    <div className="rounded-lg border border-sky-500/20 bg-sky-500/[4%] overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-sky-500/[8%] border-b border-sky-500/15">
        <Globe size={11} className="text-sky-400" />
        <span className="text-[10.5px] font-mono text-sky-300">web_search</span>
        {data.query && <span className="text-[10.5px] text-zinc-400 truncate">"{data.query}"</span>}
        <span className="ml-auto text-[10px] text-sky-400/60 tabular-nums">
          {data.count ?? data.results.length} Treffer
        </span>
      </div>
      {data.results.length === 0 ? (
        <div className="px-3 py-2 text-[11px] text-zinc-500 italic">Keine Treffer.</div>
      ) : (
        <ul className="divide-y divide-sky-500/10">
          {data.results.map((r, i) => (
            <li key={i} className="px-3 py-2">
              <a href={r.url} target="_blank" rel="noopener noreferrer"
                className="block text-[12px] text-sky-300 hover:text-sky-200 hover:underline truncate font-medium">
                {r.title || r.url}
              </a>
              <div className="text-[10px] text-zinc-500 truncate font-mono">{r.url}</div>
              {r.snippet && (
                <p className="text-[11px] text-zinc-400 mt-0.5 line-clamp-2">{r.snippet}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
