import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Search } from "lucide-react"
import { dataminingApi, type SearchParams } from "./api"
import { fmtTime, TYPE_COLORS, type DmEvent } from "./types"

const EVENT_TYPES = ["user_input", "assistant_text", "tool_call", "tool_result", "thinking", "compaction"]

export function SearchTab() {
  const { t } = useTranslation("datamining")
  const [q, setQ] = useState("")
  const [eventType, setEventType] = useState("")
  const [semantic, setSemantic] = useState(false)
  const [results, setResults] = useState<DmEvent[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    try {
      const params: SearchParams = { q: q.trim(), semantic, limit: 50 }
      if (eventType) params.event_type = eventType
      const data = await dataminingApi.search(params)
      if (data.error) setError(data.error)
      setResults(data.results)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex flex-col gap-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("search.placeholder")}
            className="flex-1 bg-white/[4%] border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-white/20"
          />
          <button
            type="submit"
            disabled={loading || !q.trim()}
            className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 text-amber-300 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Search size={13} />
            {t("search.submit")}
          </button>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="bg-white/[4%] border border-white/[8%] rounded-lg px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-white/20"
          >
            <option value="">{t("search.filter_type_all")}</option>
            {EVENT_TYPES.map((et) => (
              <option key={et} value={et}>{et}</option>
            ))}
          </select>

          <label className="flex items-center gap-2 cursor-pointer">
            <div
              onClick={() => setSemantic(!semantic)}
              className={`w-8 h-4 rounded-full transition-colors relative ${semantic ? "bg-violet-500" : "bg-zinc-700"}`}
            >
              <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all ${semantic ? "left-[18px]" : "left-0.5"}`} />
            </div>
            <span className="text-xs text-zinc-400">{t("search.toggle_semantic")}</span>
          </label>
        </div>
      </form>

      {error && (
        <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
          {t("search.error", { message: error })}
        </div>
      )}

      {results !== null && (
        <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
            <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
              {t("search.results_count", { count: results.length })}
            </span>
          </div>
          {results.length === 0 ? (
            <div className="flex items-center justify-center h-20 text-zinc-600 text-sm">{t("search.no_results")}</div>
          ) : (
            <div className="max-h-96 overflow-y-auto divide-y divide-white/[3%]">
              {results.map((r) => (
                <div key={r.id} className="px-3 py-2 hover:bg-white/[3%]">
                  <div className="flex items-center gap-2 text-[10px] mb-1">
                    <span className="text-zinc-600">{fmtTime(r.created_at)}</span>
                    <span className={`px-1 rounded font-medium ${TYPE_COLORS[r.event_type] ?? "text-zinc-400 bg-zinc-500/10"}`}>
                      {r.event_type}
                    </span>
                    {r.agent_name && <span className="text-zinc-500">{r.agent_name}</span>}
                    {r.tool_name && <span className="text-zinc-600">{r.tool_name}</span>}
                    {r.is_error && <span className="text-rose-400">ERR</span>}
                    {r.similarity !== undefined && (
                      <span className="text-violet-400 ml-auto">{Math.round(r.similarity * 100)}%</span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-400 font-mono leading-relaxed line-clamp-3">{r.snippet}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
