/**
 * Bild-Thumbnail mit Klick-zum-Vergrößern (Lightbox-Overlay).
 *
 * Thumbnail und Overlay nutzen dieselbe URL (/api/files liefert das Original) —
 * die Vorschau ist nur per CSS verkleinert, das Overlay zeigt volle Größe.
 * Download-Button lädt das Original mit sinnvollem Dateinamen.
 */
import { useEffect, useState } from "react"
import { Download, X } from "lucide-react"

function fileNameFromUrl(url: string): string {
  const raw = url.split("path=")[1]?.split("&")[0] ?? ""
  return decodeURIComponent(raw).split("/").pop() || "bild.png"
}

export function ImageLightbox({ url }: { url: string }) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      window.removeEventListener("keydown", onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open])

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Bild in Originalgröße anzeigen"
        className="group block cursor-zoom-in rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/60"
      >
        <img
          src={url}
          alt=""
          className="max-w-xs max-h-64 rounded-xl object-contain border border-white/10 shadow-md transition duration-200 group-hover:brightness-110 group-hover:border-white/25"
        />
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4"
        >
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <a
              href={url}
              download={fileNameFromUrl(url)}
              onClick={(e) => e.stopPropagation()}
              title="Original herunterladen"
              aria-label="Bild herunterladen"
              className="flex items-center justify-center w-10 h-10 rounded-full bg-white/10 text-white/90 hover:bg-white/20 hover:text-white transition-colors backdrop-blur"
            >
              <Download size={18} />
            </a>
            <button
              type="button"
              onClick={() => setOpen(false)}
              title="Schließen (Esc)"
              aria-label="Schließen"
              className="flex items-center justify-center w-10 h-10 rounded-full bg-white/10 text-white/90 hover:bg-white/20 hover:text-white transition-colors backdrop-blur"
            >
              <X size={18} />
            </button>
          </div>
          <img
            src={url}
            alt=""
            onClick={(e) => e.stopPropagation()}
            className="max-w-[92vw] max-h-[92vh] object-contain rounded-lg shadow-2xl cursor-zoom-out"
          />
        </div>
      )}
    </>
  )
}
