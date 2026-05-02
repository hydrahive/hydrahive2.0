import { useEffect, useState } from "react"
import { wikiApi } from "./api"
import { PageList } from "./PageList"
import { PageDetail } from "./PageDetail"
import { PageEditor } from "./PageEditor"
import type { WikiPage as TWikiPage } from "./types"

type Mode = "view" | "edit" | "new"

export function WikiPage() {
  const [pages, setPages] = useState<TWikiPage[]>([])
  const [selected, setSelected] = useState<TWikiPage | null>(null)
  const [mode, setMode] = useState<Mode>("view")
  const [loading, setLoading] = useState(true)

  async function load(q?: string) {
    setLoading(true)
    try {
      const list = await wikiApi.list(q)
      setPages(list)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function selectSlug(slug: string) {
    const page = await wikiApi.get(slug)
    setSelected(page)
    setMode("view")
  }

  async function handleDelete() {
    if (!selected || !confirm(`"${selected.title}" löschen?`)) return
    await wikiApi.delete(selected.slug)
    setSelected(null)
    setMode("view")
    load()
  }

  function handleSaved(page: TWikiPage) {
    setSelected(page)
    setMode("view")
    load()
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-0 rounded-xl border border-white/[6%] overflow-hidden bg-zinc-950/50">
      {/* Sidebar */}
      <div className="w-64 shrink-0 border-r border-white/[6%] overflow-hidden flex flex-col">
        <div className="px-3 py-2.5 border-b border-white/[6%]">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Wiki</h2>
        </div>
        {loading ? (
          <p className="text-xs text-zinc-600 text-center mt-8">Lädt…</p>
        ) : (
          <PageList
            pages={pages}
            selected={selected?.slug ?? null}
            onSelect={selectSlug}
            onNew={() => { setSelected(null); setMode("new") }}
            onSearch={(q) => load(q || undefined)}
          />
        )}
      </div>

      {/* Main */}
      <div className="flex-1 overflow-hidden">
        {mode === "new" && (
          <PageEditor
            page={null}
            onSaved={handleSaved}
            onCancel={() => setMode("view")}
          />
        )}
        {mode === "edit" && selected && (
          <PageEditor
            page={selected}
            onSaved={handleSaved}
            onCancel={() => setMode("view")}
          />
        )}
        {mode === "view" && selected && (
          <PageDetail
            page={selected}
            onEdit={() => setMode("edit")}
            onDelete={handleDelete}
            onNavigate={selectSlug}
          />
        )}
        {mode === "view" && !selected && (
          <div className="flex items-center justify-center h-full text-zinc-600 text-sm">
            Seite auswählen oder neue erstellen
          </div>
        )}
      </div>
    </div>
  )
}
