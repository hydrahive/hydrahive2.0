import { Trash2 } from "lucide-react"
import type { MediaCutPoint, MediaTransitionEffect } from "../../mediaWorkspaceApi"
import { timecode } from "./useCutPlayback"
import { TRANSITIONS } from "./transitions"

interface Props {
  cut: MediaCutPoint
  onChange: (patch: Partial<MediaCutPoint>) => void
  onRemove: () => void
  onClose: () => void
}

const DEFAULT_DURATION = 1

/** Inspector für einen ausgewählten Schnittpunkt: Übergangseffekt + Dauer. */
export function CutPointInspector({ cut, onChange, onRemove, onClose }: Props) {
  const effect = cut.effect ?? "cut"
  const duration = cut.duration ?? 0

  const selectEffect = (next: MediaTransitionEffect) => {
    // Beim Wechsel von Hartschnitt auf einen Übergang eine sinnvolle Default-Dauer setzen.
    if (next !== "cut" && duration <= 0) onChange({ effect: next, duration: DEFAULT_DURATION })
    else if (next === "cut") onChange({ effect: next })
    else onChange({ effect: next })
  }

  return (
    <div className="mt-3 rounded-[4px] border border-rose-500/30 bg-[#141b28] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-rose-300">
          Schnittpunkt · {timecode(cut.time)}
        </span>
        <button onClick={onClose} className="text-[10px] uppercase tracking-[0.12em] text-[#68758a] hover:text-[#c3ccdd]">
          schließen
        </button>
      </div>

      {/* Effekt-Auswahl */}
      <div className="flex flex-wrap gap-1.5">
        {TRANSITIONS.map((t) => (
          <button
            key={t.id}
            onClick={() => selectEffect(t.id)}
            className={["rounded-[3px] border px-2 py-1 text-[11px] font-semibold transition-colors",
              effect === t.id
                ? "border-rose-400/60 bg-rose-500/15 text-rose-100"
                : "border-[#2a364b] bg-[#111827] text-[#8d9ab0] hover:text-[#c3ccdd]"].join(" ")}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Dauer-Slider (nur bei echten Übergängen) */}
      {effect !== "cut" ? (
        <div className="mt-3 flex items-center gap-2">
          <span className="text-[11px] text-[#8d9ab0]">Dauer</span>
          <input
            type="range" min={0.2} max={5} step={0.1} value={duration || DEFAULT_DURATION}
            onChange={(e) => onChange({ duration: Number(e.target.value) })}
            className="h-1 flex-1 cursor-pointer accent-rose-400"
          />
          <span className="w-12 text-right font-mono text-[11px] text-rose-200">{(duration || DEFAULT_DURATION).toFixed(1)}s</span>
        </div>
      ) : (
        <p className="mt-2 text-[11px] text-[#68758a]">Hartschnitt — kein Übergang.</p>
      )}

      <button
        onClick={onRemove}
        className="mt-3 inline-flex items-center gap-1.5 rounded-[3px] border border-[#2a364b] px-2 py-1 text-[11px] text-rose-300 hover:bg-rose-500/10"
      >
        <Trash2 size={12} /> Schnittpunkt löschen
      </button>
    </div>
  )
}
