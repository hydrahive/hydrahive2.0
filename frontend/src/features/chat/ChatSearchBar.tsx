import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronUp, X } from "lucide-react"
import { useChatSearch } from "./ChatSearchContext"

export function ChatSearchBar({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("chat")
  const { query, setQuery, activeIdx, matchCount, next, prev } = useChatSearch()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") { setQuery(""); onClose() }
    else if (e.key === "Enter") { e.preventDefault(); if (e.shiftKey) prev(); else next() }
    else if (e.key === "F3") { e.preventDefault(); if (e.shiftKey) prev(); else next() }
  }

  const hasQuery = query.trim().length > 0

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[6%] bg-zinc-950/80 backdrop-blur shrink-0">
      <input
        ref={inputRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("session.new_chat")}
        className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none"
      />
      {hasQuery && (
        <span className={`text-xs tabular-nums whitespace-nowrap ${matchCount === 0 ? "text-rose-400" : "text-zinc-400"}`}>
          {matchCount === 0 ? t("session.no_sessions") : `${activeIdx + 1} / ${matchCount}`}
        </span>
      )}
      <button onClick={prev} disabled={matchCount === 0} title={t("search.prev")}
        className="p-1 rounded text-zinc-500 hover:text-zinc-200 disabled:opacity-30 transition-colors">
        <ChevronUp size={14} />
      </button>
      <button onClick={next} disabled={matchCount === 0} title={t("search.next")}
        className="p-1 rounded text-zinc-500 hover:text-zinc-200 disabled:opacity-30 transition-colors">
        <ChevronDown size={14} />
      </button>
      <button onClick={() => { setQuery(""); onClose() }} title={t("search.close")}
        className="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors">
        <X size={14} />
      </button>
    </div>
  )
}
