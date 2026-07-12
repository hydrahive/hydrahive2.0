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
  onRemove: () => void
}

function fmtDur(s: number): string {
  if (s >= 60) return `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
  return `${Math.round(s * 10) / 10}s`
}

/** Ein horizontal verschiebbarer Clip. Snapping an fremde Kanten/0/Cursor —
 *  sowohl Start- als auch Endkante rastet ein. Überlappung ist erlaubt. */
export function ClipBlock({ clip, label, tone, pxPerSecond, snapTargets, onPreview, onCommit, onRemove }: Props) {
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
      <p className="truncate text-[9px] font-semibold leading-3 text-[#e8eef8]">{label}</p>
      <p className="font-mono text-[8px] text-[#8d9ab0]">{fmtDur(clip.duration)}</p>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={onRemove}
        aria-label="Clip entfernen"
        className="absolute right-0.5 top-0.5 hidden rounded-[2px] bg-black/60 p-0.5 text-zinc-300 hover:text-white group-hover:block">
        <X size={9} />
      </button>
    </div>
  )
}
