import { X } from "lucide-react"
import { useCallback, type PointerEvent } from "react"
import type { MediaCutPoint } from "../../mediaWorkspaceApi"
import { useDragX } from "./useDragX"

const SNAP_THRESHOLD = 0.4

interface Props {
  cut: MediaCutPoint
  pxPerSecond: number
  /** Absoluter Left-Offset der Spurspalte (Label-Breite + Gap). */
  laneOffsetCss: string
  /** Snap-Ziele in Sekunden (Clip-Kanten, 0). */
  snapTargets: number[]
  onPreview: (time: number) => void
  onCommit: (time: number) => void
  onRemove: () => void
}

/** Weißer, vertikal über alle Spuren gehender Schnittpunkt-Marker. Ziehbar
 *  (mit Snapping an Clip-Kanten), löschbar. Der Griff sitzt unten am Marker. */
export function CutPointMarker({ cut, pxPerSecond, laneOffsetCss, snapTargets, onPreview, onCommit, onRemove }: Props) {
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
    start(e, cut.time)
  }, [start, cut.time])

  return (
    <div
      className="group/cut absolute inset-y-0 z-30 w-[2px] bg-white"
      style={{ left: `calc(${laneOffsetCss} + ${cut.time * pxPerSecond}px)` }}
    >
      {/* Griff oben: ziehen */}
      <div
        onPointerDown={onPointerDown}
        title="Schnittpunkt ziehen"
        className={["absolute -top-1 -left-[5px] h-3 w-3 cursor-ew-resize touch-none rounded-[2px] border border-white bg-[#0d1420]",
          dragging ? "ring-2 ring-white/70" : ""].join(" ")}
      />
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
