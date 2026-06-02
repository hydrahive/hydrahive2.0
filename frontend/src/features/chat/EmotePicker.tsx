import { useEffect, useRef, useState } from "react"
import { Smile } from "lucide-react"
import { HYDRA_EMOTES, EMOTE_NAMES } from "./hydraEmotes"

// Nur kanonische Emotes im Picker (Aliase wie heart/laughing nicht doppelt zeigen).
const PICKER = EMOTE_NAMES.map((n) => [n, HYDRA_EMOTES[n]] as const)

/** Button + Raster-Popover. Klick auf ein Emote ruft onPick(":hydra-name:"). */
export function EmotePicker({ onPick, disabled }: { onPick: (shortcode: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onDoc)
    return () => document.removeEventListener("mousedown", onDoc)
  }, [open])

  return (
    <div ref={ref} className="relative flex-shrink-0">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        title="Hydra-Emoticons"
        className={`p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
          open ? "text-violet-300 bg-violet-500/15" : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
        }`}
      >
        <Smile size={15} />
      </button>
      {open && (
        <div className="absolute bottom-full mb-2 left-0 z-30 grid grid-cols-7 gap-1 p-2 rounded-xl bg-zinc-900/95 backdrop-blur border border-white/10 shadow-xl shadow-black/50 w-max max-h-[280px] overflow-y-auto">
          {PICKER.map(([name, src]) => (
            <button
              key={name}
              type="button"
              title={name}
              onClick={() => {
                onPick(`:hydra-${name}:`)
                setOpen(false)
              }}
              className="p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              <img src={src} alt={name} className="w-8 h-8 object-contain" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
