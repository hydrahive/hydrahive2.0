import { useEffect, useState } from "react"
import { Loader2, Save, X } from "lucide-react"
import { wikiApi } from "./api"
import type { WikiPage } from "./types"

interface Props {
  page: WikiPage | null
  onSaved: (page: WikiPage) => void
  onCancel: () => void
}

export function PageEditor({ page, onSaved, onCancel }: Props) {
  const [title, setTitle] = useState(page?.title ?? "")
  const [body, setBody] = useState(page?.body ?? "")
  const [tags, setTags] = useState(page?.tags.join(", ") ?? "")
  const [entities, setEntities] = useState(page?.entities.join(", ") ?? "")
  const [sourceUrl, setSourceUrl] = useState(page?.source_url ?? "")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    setTitle(page?.title ?? "")
    setBody(page?.body ?? "")
    setTags(page?.tags.join(", ") ?? "")
    setEntities(page?.entities.join(", ") ?? "")
    setSourceUrl(page?.source_url ?? "")
    setError("")
  }, [page?.slug])

  function splitList(s: string): string[] {
    return s.split(",").map((v) => v.trim()).filter(Boolean)
  }

  async function handleSave() {
    if (!title.trim()) { setError("Titel fehlt"); return }
    setSaving(true); setError("")
    try {
      const data = { title: title.trim(), body, tags: splitList(tags), entities: splitList(entities), source_url: sourceUrl }
      const saved = page ? await wikiApi.update(page.slug, data) : await wikiApi.create(data)
      onSaved(saved)
    } catch (e: any) {
      setError(e?.message ?? "Fehler beim Speichern")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-3 border-b border-white/[6%]">
        <span className="text-xs font-medium text-zinc-300 flex-1">
          {page ? "Seite bearbeiten" : "Neue Seite"}
        </span>
        <button onClick={onCancel} className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/[5%]">
          <X size={14} />
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-violet-600 text-white text-xs hover:bg-violet-500 disabled:opacity-50"
        >
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          Speichern
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {error && <p className="text-xs text-red-400 bg-red-500/10 rounded px-3 py-2">{error}</p>}

        <div>
          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Titel</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50"
          />
        </div>

        <div className="flex-1 flex flex-col">
          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Inhalt (Markdown, [[WikiLinks]])</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="mt-1 flex-1 min-h-[200px] w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-sm text-zinc-200 font-mono focus:outline-none focus:border-violet-500/50 resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Tags (kommagetrennt)</label>
            <input value={tags} onChange={(e) => setTags(e.target.value)}
              className="mt-1 w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-violet-500/50" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Entitäten</label>
            <input value={entities} onChange={(e) => setEntities(e.target.value)}
              className="mt-1 w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-violet-500/50" />
          </div>
        </div>

        <div>
          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Quell-URL (optional)</label>
          <input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)}
            className="mt-1 w-full bg-white/[4%] border border-white/[8%] rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-violet-500/50" />
        </div>
      </div>
    </div>
  )
}
