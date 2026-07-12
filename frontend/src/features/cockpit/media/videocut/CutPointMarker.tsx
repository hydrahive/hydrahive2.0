import { X } from "lucide-react"
import { useCallback, type PointerEvent } from "react"
import type { MediaCutPoint } from "../../mediaWorkspaceApi"
import { transitionShort } from "./transitions"
import { useDragX } from "./useDragX"

const SNAP_THRESHOLD = 0.4

interface Props {
  cut: MediaCutPoint
  pxPerSecond: number
  /** Absoluter Left-Offset der Spurspalte (Label-Breite + Gap). */
  laneOffsetCss: string
  /** Snap-Ziele in Sekunden (Clip-Kanten, 0). */
  snapTargets: number[]
  selected: boolean
  onSelect: () => void
  onPreview: (time: number) => void
  onCommit: (time: number) => void
  onRemove: () => void
}

/** Weißer, vertikal über alle Spuren gehender Schnittpunkt-Marker. Ziehbar
 *  (Snapping an Clip-Kanten), auswählbar (Klick), löschbar. Bei Übergang mit
 *  Effekt zeigt er das Effekt-Kürzel; die Übergangsdauer wird als Band angedeutet. */
export function CutPointMarker({ cut, pxPerSecond, laneOffsetCss, snapTargets, selected, onSelect, onPreview, onCommit, onRemove }: Props) {
  const snap = useCallback((value: number): number => {
    let best = value
    let bestDelta = SNAP_THRESHOLD
    for (const t of snapTargets) {
      const d = Math.abs(t - value)
      if (d < bestDelta) { bestDelta = d; best = t }
    }
    return Math.max(0, best)
  }, [snapTargets])

  const { start, dragging } = useDragX({ pxPerSecond, onMove: onPreview, onCommit, snap })

  const onPointerDown = useCallback((e: PointerEvent) => {
    if (e.button !== 0) return
    e.stopPropagation()
    onSelect()
    start(e, cut.time)
  }, [start, cut.time, onSelect])

  const effect = cut.effect ?? "cut"
  const dur = cut.duration ?? 0
  const short = transitionShort(effect)
  const bandWidth = effect !== "cut" && dur > 0 ? dur * pxPerSecond : 0
  const color = selected ? "#f43f5e" : "#ffffff"

  return (
    <div
      className="group/cut absolute inset-y-0 z-30"
      style={{ left: `calc(${laneOffsetCss} + ${cut.time * pxPerSecond}px)` }}
    >
      {/* Übergangs-Band (zentriert um den Schnittpunkt) */}
      {bandWidth > 0 ? (
        <div
          className="pointer-events-none absolute inset-y-0"
          style={{ left: `${-bandWidth / 2}px`, width: `${bandWidth}px`, background: `${color}22`, borderLeft: `1px dashed ${color}66`, borderRight: `1px dashed ${color}66` }}
        />
      ) : null}

      {/* Marker-Linie */}
      <div className="absolute inset-y-0 w-[2px]" style={{ background: color }} />

      {/* Griff oben: auswählen + ziehen */}
      <div
        onPointerDown={onPointerDown}
        title={`Schnittpunkt (${effect})`}
        className={["absolute -top-1 -left-[6px] grid h-3.5 w-3.5 cursor-ew-resize touch-none place-items-center rounded-[2px] border font-mono text-[7px] font-bold leading-none",
          selected ? "border-rose-400 text-rose-100" : "border-white text-white",
          dragging ? "ring-2 ring-white/70" : ""].join(" ")}
        style={{ background: "#0d1420" }}
      >
        {short}
      </div>

      {/* Löschen unten */}
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={onRemove}
        aria-label="Schnittpunkt löschen"
        className="absolute -bottom-1 -left-[6px] hidden rounded-[2px] bg-black/70 p-0.5 text-zinc-300 hover:text-white group-hover/cut:block"
      >
        <X size={9} />
      </button>
    </div>
  )
}
