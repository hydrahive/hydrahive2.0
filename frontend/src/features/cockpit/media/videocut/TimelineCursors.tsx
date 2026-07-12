import type { PointerEvent } from "react"

interface Props {
  laneOffsetCss: string
  playheadLeft: number
  cursorLeft: number
  onPlayheadPointerDown: (e: PointerEvent) => void
  onCursorPointerDown: (e: PointerEvent) => void
  playheadDragging: boolean
  cursorDragging: boolean
}

/** Die beiden ziehbaren Linien über den Spuren: orange Playhead (Wiedergabe)
 *  und roter Cut-Cursor (Justage der Input-Monitore). */
export function TimelineCursors({
  laneOffsetCss, playheadLeft, cursorLeft,
  onPlayheadPointerDown, onCursorPointerDown, playheadDragging, cursorDragging,
}: Props) {
  return (
    <>
      {/* Playhead-Linie (Wiedergabe) — Griff oben ziehbar zum Vor-/Zurückscrollen */}
      <div className="absolute inset-y-0 z-10 w-px bg-[#ffb86b]" style={{ left: `calc(${laneOffsetCss} + ${playheadLeft}px)` }}>
        <div
          onPointerDown={onPlayheadPointerDown}
          title="Abspielposition ziehen"
          className={["absolute -top-1.5 -left-[6px] h-3.5 w-3.5 cursor-ew-resize touch-none rounded-[2px] bg-[#ffb86b] shadow",
            playheadDragging ? "ring-2 ring-[#ffd9a8]" : ""].join(" ")}
        />
      </div>

      {/* Roter Cut-Cursor (Justage) — ziehbar */}
      <div className="absolute inset-y-0 z-20 w-[2px] touch-none bg-rose-500" style={{ left: `calc(${laneOffsetCss} + ${cursorLeft}px)` }}>
        <div
          onPointerDown={onCursorPointerDown}
          title="Cut-Cursor ziehen"
          className={["absolute -top-1 -left-[6px] h-3 w-3.5 cursor-ew-resize rounded-[2px] bg-rose-500 shadow",
            cursorDragging ? "ring-2 ring-rose-300" : ""].join(" ")}
        />
      </div>
    </>
  )
}
