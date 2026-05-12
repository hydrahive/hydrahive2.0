/**
 * Inline-EPUB-Viewer via epub.js — klappt auf Klick auf, wie PdfViewer.
 * Rendert EPUB-Inhalt direkt im Browser ohne Plugin oder Konvertierung.
 */
import { useEffect, useRef, useState } from "react"
import Epub, { type Book, type Rendition } from "epubjs"

interface Props {
  url: string
  name: string
}

export function EpubViewer({ url, name }: Props) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const bookRef = useRef<Book | null>(null)
  const renditionRef = useRef<Rendition | null>(null)

  useEffect(() => {
    if (!open) return
    if (!containerRef.current) return

    setLoading(true)
    setError(null)

    const book = Epub(url)
    bookRef.current = book

    const rendition = book.renderTo(containerRef.current, {
      width: "100%",
      height: "100%",
      flow: "paginated",
    })
    renditionRef.current = rendition

    rendition.display().then(() => setLoading(false)).catch((e: unknown) => {
      setError(String(e))
      setLoading(false)
    })

    return () => {
      rendition.destroy()
      book.destroy()
      bookRef.current = null
      renditionRef.current = null
    }
  }, [open, url])

  function prev() { renditionRef.current?.prev() }
  function next() { renditionRef.current?.next() }

  return (
    <div className="w-4/5">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-3 px-4 py-3 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors w-full text-left"
      >
        <span className="text-2xl">📖</span>
        <span className="text-sm flex-1 truncate">{name}</span>
        <span className="text-xs text-white/40">{open ? "▲ schließen" : "▼ lesen"}</span>
      </button>

      {open && (
        <div className="rounded-b-xl border border-t-0 border-white/10 overflow-hidden" style={{ height: "80vh" }}>
          {loading && (
            <div className="flex items-center justify-center h-full text-white/40 text-sm">
              Lade EPUB…
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-full text-red-400 text-sm p-4">
              Fehler: {error}
            </div>
          )}
          <div ref={containerRef} className="w-full h-full" />
          {!loading && !error && (
            <div className="flex justify-between px-4 py-2 bg-black/20 border-t border-white/10">
              <button onClick={prev} className="text-sm text-white/60 hover:text-white px-3 py-1 rounded hover:bg-white/10 transition-colors">← zurück</button>
              <button onClick={next} className="text-sm text-white/60 hover:text-white px-3 py-1 rounded hover:bg-white/10 transition-colors">weiter →</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
