import { X } from "lucide-react"
import { useEffect } from "react"

export interface LightboxSource {
  url: string
  kind: "video" | "image" | "audio"
  label?: string
}

interface Props {
  source: LightboxSource | null
  onClose: () => void
}

/** Vollbild-Vorschau (Modal) für einen Clip/Film: Video mit Steuerung, Bild
 *  oder Audio. Klick auf den Hintergrund oder Esc schließt. */
export function MediaLightbox({ source, onClose }: Props) {
  useEffect(() => {
    if (!source) return
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [source, onClose])

  if (!source) return null

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-black/80 p-6" onClick={onClose}>
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col gap-2" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <span className="truncate font-mono text-[12px] text-[#c3ccdd]" title={source.label}>{source.label ?? ""}</span>
          <button onClick={onClose} aria-label="Schließen" className="grid h-8 w-8 place-items-center rounded-[4px] border border-white/20 bg-white/5 text-white hover:bg-white/10">
            <X size={16} />
          </button>
        </div>
        <div className="grid min-h-0 place-items-center overflow-hidden rounded-lg border border-white/10 bg-black">
          {source.kind === "video" ? (
            <video src={source.url} controls autoPlay className="max-h-[80vh] w-full object-contain" />
          ) : source.kind === "image" ? (
            <img src={source.url} alt={source.label ?? ""} className="max-h-[80vh] w-full object-contain" />
          ) : (
            <div className="w-full p-8">
              <audio src={source.url} controls autoPlay className="w-full" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
