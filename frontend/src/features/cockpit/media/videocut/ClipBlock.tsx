import { X } from "lucide-react"
import { useCallback, type PointerEvent } from "react"
import type { MediaTimelineClip } from "../../mediaWorkspaceApi"
import { useDragX } from "./useDragX"

const SNAP_THRESHOLD = 0.4

interface Props {
  clip: MediaTimelineClip
  label: string
  tone: string
  pxPerSecond: number
  /** Snap-Ziele in Sekunden (fremde Clip-Kanten, 0, Cursor). */
  snapTargets: number[]
  onPreview: (start: number) => void
  onCommit: (start: number) => void
  /** Trim: Kante live ziehen (preview) + persistieren (commit). */
  onTrimPreview: (edge: "start" | "end", value: number) => void
  onTrimCommit: (edge: "start" | "end", value: number) => void
  onRemove: () => void
}

function fmtDur(s: number): string {
  if (s >= 60) return `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
  return `${Math.round(s * 10) / 10}s`
}

/** Kleiner Trim-Griff an einer Clip-Kante. Eigene Komponente wegen useDragX-Hook. */
function TrimHandle({ side, edgeTime, pxPerSecond, onPreview, onCommit }: {
  side: "left" | "right"
  edgeTime: number
  pxPerSecond: number
  onPreview: (value: number) => void
  onCommit: (value: number) => void
}) {
  const { start, dragging } = useDragX({ pxPerSecond, onMove: onPreview, onCommit })
  const onPointerDown = useCallback((e: PointerEvent) => {
    if (e.button !== 0) return
    e.stopPropagation()
    start(e, edgeTime)
  }, [start, edgeTime])
  return (
    <div
      onPointerDown={onPointerDown}
      title={side === "left" ? "Anfang trimmen" : "Ende trimmen"}
      className={["absolute inset-y-0 z-10 w-2 cursor-ew-resize touch-none",
        side === "left" ? "left-0" : "right-0",
        dragging ? "bg-white/70" : "bg-white/0 hover:bg-white/40"].join(" ")}
    />
  )
}

/** Ein horizontal verschiebbarer Clip mit Trim-Handles an beiden Kanten.
 *  Body-Drag verschiebt (Snap an Kanten/0/Cursor), Kanten-Handles trimmen. */
export function ClipBlock({ clip, label, tone, pxPerSecond, snapTargets, onPreview, onCommit, onTrimPreview, onTrimCommit, onRemove }: Props) {
  const snap = useCallback((value: number): number => {
    let best = value
    let bestDelta = SNAP_THRESHOLD
    for (const t of snapTargets) {
      const dStart = Math.abs(t - value)
      if (dStart < bestDelta) { bestDelta = dStart; best = t }
      const dEnd = Math.abs(t - (value + clip.duration))
      if (dEnd < bestDelta) { bestDelta = dEnd; best = t - clip.duration }
    }
    return Math.max(0, best)
  }, [snapTargets, clip.duration])

  const { start, dragging } = useDragX({ pxPerSecond, onMove: onPreview, onCommit, snap })

  const onPointerDown = useCallback((e: PointerEvent) => {
    if (e.button !== 0) return
    start(e, clip.start)
  }, [start, clip.start])

  return (
    <div
      onPointerDown={onPointerDown}
      className={["group absolute inset-y-1 select-none touch-none overflow-hidden rounded-[3px] border px-1.5 py-0.5",
        dragging ? "cursor-grabbing ring-1 ring-white/40" : "cursor-grab"].join(" ")}
      style={{
        left: `${clip.start * pxPerSecond}px`,
        width: `${Math.max(clip.duration * pxPerSecond, 34)}px`,
        borderColor: tone,
        background: `${tone}22`,
      }}
      title={`${label} · ${fmtDur(clip.duration)}`}>
      <TrimHandle side="left" edgeTime={clip.start} pxPerSecond={pxPerSecond}
        onPreview={(v) => onTrimPreview("start", v)} onCommit={(v) => onTrimCommit("start", v)} />
      <TrimHandle side="right" edgeTime={clip.start + clip.duration} pxPerSecond={pxPerSecond}
        onPreview={(v) => onTrimPreview("end", v)} onCommit={(v) => onTrimCommit("end", v)} />

      <p className="truncate text-[9px] font-semibold leading-3 text-[#e8eef8]">{label}</p>
      <p className="font-mono text-[8px] text-[#8d9ab0]">{fmtDur(clip.duration)}</p>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={onRemove}
        aria-label="Clip entfernen"
        className="absolute right-1.5 top-0.5 z-20 hidden rounded-[2px] bg-black/60 p-0.5 text-zinc-300 hover:text-white group-hover:block">
        <X size={9} />
      </button>
    </div>
  )
}
