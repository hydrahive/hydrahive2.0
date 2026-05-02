import { useState } from "react"
import { Link2, Loader2, Type, X } from "lucide-react"
import { wikiApi } from "./api"
import type { WikiPage } from "./types"

interface Props {
  onDone: (page: WikiPage) => void
  onCancel: () => void
}

type Mode = "url" | "text"

export function IngestForm({ onDone, onCancel }: Props) {
  const [mode, setMode] = useState<Mode>("url")
  const [url, setUrl] = useState("")
  const [text, setText] = useState("")
  const [title, setTitle] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit() {
    if (mode === "url" && !url.trim()) { setError("URL fehlt"); return }
    if (mode === "text" && !text.trim()) { setError("Text fehlt"); return }
    setLoading(true); setError("")
    try {
      const page = await wikiApi.ingest({
        url: mode === "url" ? url.trim() : undefined,
        text: mode === "text" ? text.trim() : undefined,
        title: title.trim() || undefined,
      })
      onDone(page)
    } catch (e: any) {
      setError(e?.message ?? "Fehler bei der Ingestion")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-3 border-b border-white/[6%]">
        <span className="text-xs font-medium text-zinc-300 flex-1">Inhalt aufnehmen</span>
        <button onClick={onCancel} className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/[5%]">
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Mode Toggle */}
        <div className="flex gap-1 p-1 bg-white/[4%] rounded-lg w-fit">
          <button
            onClick={() => setMode("url")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors ${mode === "url" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            <Link2 size={12} /> URL
          </button>
          <button
            onClick={() => setMode("text")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors ${mode === "text" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            <Type size={12} /> Text
          </button>
        </div>

        {error && <p className="text-xs text-red-400 bg-red-500/10 rounded px-3 py-2">{error}</p>}

        {mode === "url" ? (
          <div>
            <label className="text-[10px] text-zinc-500 uppercase tracking-wide">URL</label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://..."
              className="mt-1 w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50"
            />
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Text</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Text einfügen…"
              className="mt-1 flex-1 min-h-[160px] w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50 resize-none"
            />
          </div>
        )}

        <div>
          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Titel (optional — LLM erkennt ihn sonst selbst)</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Automatisch erkennen"
            className="mt-1 w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50"
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors"
        >
          {loading ? (
            <><Loader2 size={14} className="animate-spin" /> LLM analysiert…</>
          ) : (
            "Aufnehmen"
          )}
        </button>

        {loading && (
          <p className="text-xs text-zinc-500 text-center">
            {mode === "url" ? "Seite wird geladen und analysiert…" : "Text wird analysiert…"} Das dauert 5–15 Sekunden.
          </p>
        )}
      </div>
    </div>
  )
}
